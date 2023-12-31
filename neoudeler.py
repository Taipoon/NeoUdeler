from __future__ import annotations

import dataclasses
import datetime
import enum
import logging
import os
import shutil
from threading import Lock

import colorama
import dotenv
import pathvalidate
import requests
from colorama import Fore

logger = logging.getLogger(__name__)

colorama.init(autoreset=True)

logging.basicConfig(
    filename='neo_udeler.log',
    level=logging.ERROR,
    datefmt='%Y/%m/%d %H:%I:%S %p',
)


class NeoUdelerError(Exception):
    """
    NeoUdeler で発生するエラーは NeoUdelerError を基底クラスとして送出されます。
    """
    pass


def write_log(response: requests.Response):
    logger.info(f'URL: {response.url}, HTTP status code: {response.status_code}')


def check_response(response: requests.Response):
    """
    requests.Response の HTTP ステータスコードが 200 OK でない場合は例外を送出します。

    :param response: HTTP レスポンス
    :return:
    """
    if response.status_code != 200:
        write_log(response)
        raise NeoUdelerError(f'Error with status code: {response.status_code} at {response.url}')


def download(url: str, path: str, chunking: bool = False):
    """
    urlで指定したコンテンツを path に保存します。
    :param url: データ取得元URL
    :param path: 保存先ファイルパス
    :param chunking: 分割ダウンロードを行うかどうか
    :return:
    """
    response = requests.get(url, stream=chunking)
    check_response(response)
    with open(path, 'wb') as file:
        if chunking:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
        else:
            file.write(response.content)


def mkdir_unless_already_exists(dir_path: str):
    if os.path.isdir(dir_path):
        raise NeoUdelerError(f'{dir_path}: already exists')

    os.mkdir(dir_path)


class VideoFormat(enum.StrEnum):
    """
    Udemy が提供する動画のフォーマット形式の種類を表します。
    """
    VIDEO_MPEG4 = 'video/mp4'
    APPLICATION_X_MPEG_URL = 'application/x-mpegURL'

    def is_mp4(self) -> bool:
        return self == VideoFormat.VIDEO_MPEG4

    def is_hls(self) -> bool:
        return self == VideoFormat.APPLICATION_X_MPEG_URL


class AssetType(enum.StrEnum):
    """
    Udemy の「レクチャー」に紐づくアセットの種類を表します。
    """
    VIDEO = 'Video'
    ARTICLE = 'Article'
    FILE = 'File'
    E_BOOK = 'E-book'
    EXTERNAL_LINK = 'ExternalLink'


class CourseContentType(enum.StrEnum):
    """
    Udemy のコンテンツの種類を表します。

    Udemy のコンテンツは「チャプター」と「レクチャー」の2種類があります。

    チャプター：
    ・「レクチャー」をグルーピングする役割を担います。
    ・Web UI上ではセクションとして表示されます。

    レクチャー：
    ・受講者が利用する講義動画、ファイル(資料)などのアセットを管理します。
    """
    CHAPTER = 'chapter'
    LECTURE = 'lecture'
    QUIZ = 'quiz'


@dataclasses.dataclass
class Asset(object):
    """
    Udemy のコースを構成する
    """
    asset_id: int
    asset_type: AssetType
    title: str
    description: str
    body: str
    stream_urls: StreamUrls | None
    download_urls: DownloadUrls | None

    def is_video(self) -> bool:
        return self.asset_type == AssetType.VIDEO

    def is_article(self) -> bool:
        return self.asset_type == AssetType.ARTICLE

    def is_file(self) -> bool:
        return self.asset_type == AssetType.FILE

    def is_e_book(self) -> bool:
        return self.asset_type == AssetType.E_BOOK

    def is_external_link(self) -> bool:
        return self.asset_type == AssetType.EXTERNAL_LINK


@dataclasses.dataclass
class Video(object):
    """
    Udemy の講義動画を表します。
    """
    video_format: VideoFormat
    quality_label: str
    file_url: str


@dataclasses.dataclass
class File(object):
    label: str
    file_url: str


@dataclasses.dataclass
class StreamUrls(object):
    """
    レクチャーに紐づく動画のURLのリストを表します。
    """
    videos: list[Video]

    def get_mp4_by_quality(self, quality: str):
        for video in self.videos:
            if not video.video_format.VIDEO_MPEG4:
                continue

            if video.quality_label == quality:
                return video

        self._get_mp4_highest_quality()

    def _get_mp4_highest_quality(self):
        return [v for v in sorted(self.videos,
                                  key=lambda v: v.quality_label,
                                  reverse=True) if v.video_format == VideoFormat.VIDEO_MPEG4]


@dataclasses.dataclass
class DownloadUrls(object):
    files: list[File]


@dataclasses.dataclass
class SupplementaryAssets(object):
    """
    レクチャーに紐づく補足資料のリストを表します。
    """
    supplementary_assets: list[Asset]


@dataclasses.dataclass
class CourseContent(object):
    """
    Udemyのコース(講座)を構成するコンテンツを表します。
    """
    course_id: int
    course_content_id: int
    course_content_type: CourseContentType
    title: str
    description: str
    asset: Asset | None
    supplementary_assets: SupplementaryAssets | None

    def is_lecture(self) -> bool:
        return self.course_content_type == CourseContentType.LECTURE

    def is_chapter(self) -> bool:
        return self.course_content_type == CourseContentType.CHAPTER

    def is_quiz(self) -> bool:
        return self.course_content_type == CourseContentType.QUIZ


@dataclasses.dataclass
class Course(object):
    course_id: int
    title: str
    url: str
    image_480_270_url: str
    locale_title: str
    visible_instructors: list[Instructor]

    def fetch_all_contents(self) -> list[CourseContent]:
        config = Config()

        api_path = f'/api-2.0/courses/{self.course_id}/cached-subscriber-curriculum-items'
        params = {
            'page_size': 100_000,
            'fields[asset]': 'title,description,data,body,asset_type,captions,download_urls,stream_urls',
            'fields[lecture]': 'title,description,asset,supplementary_assets',
        }

        response = requests.get(config.udemy_base_url + api_path,
                                params=params,
                                cookies={'access_token': config.access_token})
        check_response(response)

        json_data = response.json()
        results = json_data.get('results')

        return self._create_course_contents_list(results)

    def _create_course_contents_list(self, results: list[dict]) -> list[CourseContent]:
        course_contents = []
        for result in results:

            asset_results = result.get('asset')
            if asset_results is not None:
                asset = self._create_asset(asset_results)
            else:
                asset = None

            supplementary_assets_results = result.get('supplementary_assets')
            if supplementary_assets_results is not None:
                supplementary_assets = self._create_supplementary_assets_list(supplementary_assets_results)
            else:
                supplementary_assets = None

            course_contents.append(CourseContent(
                course_id=self.course_id,
                course_content_id=result.get('id'),
                course_content_type=CourseContentType(result.get('_class')),
                title=result.get('title'),
                description=result.get('description'),
                asset=asset,
                supplementary_assets=supplementary_assets,
            ))
        return course_contents

    def _create_supplementary_assets_list(self, results: list[dict]) -> SupplementaryAssets:
        assets = []
        for result in results:

            stream_urls_result = result.get('stream_urls')
            if stream_urls_result is not None:
                stream_urls = self._create_stream_urls(stream_urls_result)
            else:
                stream_urls = None

            download_urls_result = result.get('download_urls')
            if download_urls_result is not None:
                download_urls = self._create_download_urls(download_urls_result)
            else:
                download_urls = None

            assets.append(Asset(
                asset_id=result.get('id'),
                asset_type=AssetType(result.get('asset_type')),
                title=result.get('title'),
                description=result.get('description'),
                body=result.get('body'),
                stream_urls=stream_urls,
                download_urls=download_urls,
            ))
        return SupplementaryAssets(supplementary_assets=assets)

    def _create_asset(self, result: dict) -> Asset:
        stream_urls_results = result.get('stream_urls')
        if stream_urls_results is not None:
            stream_urls = self._create_stream_urls(stream_urls_results)
        else:
            stream_urls = None

        download_urls_results = result.get('download_urls')
        if download_urls_results is not None:
            download_urls = self._create_download_urls(download_urls_results)
        else:
            download_urls = None

        asset = Asset(
            asset_id=result.get('id'),
            asset_type=AssetType(result.get('asset_type')),
            title=result.get('title'),
            description=result.get('description'),
            body=result.get('body'),
            stream_urls=stream_urls,
            download_urls=download_urls,
        )
        return asset

    @staticmethod
    def _create_stream_urls(result: dict) -> StreamUrls | None:
        if result.get('Video') is None:
            return None

        videos = []
        for v in result.get('Video'):
            videos.append(Video(
                video_format=VideoFormat(v.get('type')),
                quality_label=v.get('label'),
                file_url=v.get('file'),
            ))
        return StreamUrls(videos=videos)

    @staticmethod
    def _create_download_urls(result: dict) -> DownloadUrls | None:
        if result.get('File') is None:
            return None

        files = []
        for f in result.get('File'):
            files.append(File(
                label=f.get('label'),
                file_url=f.get('file'),
            ))
        return DownloadUrls(files=files)

    def download_all_contents(self, dir_path: str) -> None:
        today = datetime.datetime.today().strftime('%Y%m%d')
        contents = self.fetch_all_contents()

        instructor_names = []
        for vi in self.visible_instructors:
            instructor_names.append(f'{vi.display_name}')

        raw_dir_name = f'{today}_{self.title} - {",".join(instructor_names)}'
        sanitized_dir_name = self._sanitize_filename(raw_dir_name)

        save_dir = os.path.join(dir_path, sanitized_dir_name)

        if not os.path.isdir(save_dir):
            os.mkdir(save_dir)

        chapter_number = 1
        lecture_number = 1

        total = len(contents)
        dirname_prefix_digits = len(str(total))
        chapter_dir = f'{str(0).zfill(dirname_prefix_digits)}_init'

        for current, content in enumerate(contents, start=1):

            self._print_progress(total=total, current=current)

            if content.is_chapter():
                raw_chapter_dir = f'{str(chapter_number).zfill(dirname_prefix_digits)}_{content.title}'
                chapter_dir = self._sanitize_filename(raw_chapter_dir)

                if os.path.isdir(os.path.join(save_dir, chapter_dir)):
                    shutil.rmtree(os.path.join(save_dir, chapter_dir))

                os.mkdir(os.path.join(save_dir, chapter_dir))

                chapter_number += 1

            if content.is_lecture():
                if content.asset.is_video():
                    try:
                        video = content.asset.stream_urls.get_mp4_by_quality('720')
                        download(url=video.file_url,
                                 path=os.path.join(
                                     save_dir,
                                     chapter_dir,
                                     f'{lecture_number}_{self._sanitize_filename(content.title)}.mp4'),
                                 chunking=True)
                    except AttributeError:
                        print(
                            f'{Fore.BLUE}[{content.title}]{Fore.RESET} is not available for download.{Fore.RESET}')
                        print(f'Number of lecture ({lecture_number}) may be DRM-protected... :(')

                if content.asset.is_article():
                    html = content.asset.body or content.asset.description
                    with open(os.path.join(save_dir, chapter_dir, f'{content.title}.html'), 'w', encoding='utf-8') as f:
                        f.write(html)

                supplementary_assets = content.supplementary_assets.supplementary_assets
                for supplementary_asset in supplementary_assets:

                    if supplementary_asset.stream_urls is not None:

                        videos = supplementary_asset.stream_urls.videos
                        for num, video in enumerate(videos, start=1):
                            download(url=video.file_url,
                                     path=os.path.join(save_dir,
                                                       chapter_dir,
                                                       self._sanitize_filename(f'{supplementary_asset.title}')))

                    if supplementary_asset.download_urls is not None:

                        files = supplementary_asset.download_urls.files
                        for num, file in enumerate(files, start=1):
                            download(url=file.file_url,
                                     path=os.path.join(save_dir,
                                                       chapter_dir,
                                                       self._sanitize_filename(f'{supplementary_asset.title}')),
                                     chunking=False)

                lecture_number += 1

        print('The course has been downloaded:', os.path.abspath(save_dir))

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        filename = pathvalidate.sanitize_filepath(filename)

        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in invalid_chars:
            filename = filename.replace(char, '')

        slash_chars = ['/', '\\']
        for char in slash_chars:
            filename = filename.replace(char, '／')

        return filename

    @staticmethod
    def _print_progress(total: int, current: int):
        progress_length = 50
        progress_percentage = (current / total) * 100
        progress_bar_filled = '=' * int((current / total) * progress_length)
        progress_bar_empty = ' ' * (progress_length - len(progress_bar_filled))
        progress_bar = f"{progress_percentage:.2f} %: [{progress_bar_filled}>{progress_bar_empty}]"
        print(progress_bar, end='\r')


@dataclasses.dataclass
class Instructor(object):
    user_id: int
    title: str
    name: str
    display_name: str
    job_title: str
    image_100_100: str
    user_url: str


@dataclasses.dataclass
class SubscribedCourseList(object):
    """
    ユーザーが登録しているコースのリストを表します。
    """
    search_keyword: str
    course_count: int
    courses: list[Course]

    def find_course_by_course_id(self, course_id: int) -> Course | None:
        for course in self.courses:
            if course.course_id == course_id:
                return course
        return None


class Singleton(type):
    _unique_instance = None
    _lock = Lock()

    def __call__(cls, *args, **kwargs):
        # Need to check if an instance exists in a thread-safe manner
        if not cls._unique_instance:
            with cls._lock:
                if not cls._unique_instance:
                    cls._unique_instance = super().__call__(*args, **kwargs)
        return cls._unique_instance


class Config(metaclass=Singleton):
    def __init__(self, env_path: str = '.env'):
        self._email = None
        self._password = None
        self._sub_domain = None
        self._access_token = None

        self._env_path = env_path
        self._load_dotenv()

    def _load_dotenv(self):
        self._email = dotenv.get_key(self._env_path, 'UDEMY_EMAIL')
        self._password = dotenv.get_key(self._env_path, 'UDEMY_PASSWORD')
        self._sub_domain = dotenv.get_key(self._env_path, 'SUB_DOMAIN')
        self._access_token = dotenv.get_key(self._env_path, 'ACCESS_TOKEN')

    @property
    def udemy_base_url(self) -> str:
        return f'https://{self._sub_domain}.udemy.com'

    @property
    def email(self) -> str:
        return self._email

    @property
    def password(self) -> str:
        return self._password

    @property
    def access_token(self) -> str | None:
        return self._access_token if self._access_token != '' else None

    @access_token.setter
    def access_token(self, token: str):
        self._access_token = token
        dotenv.set_key(dotenv_path=self._env_path,
                       key_to_set='ACCESS_TOKEN',
                       value_to_set=token)


class UdemyDownloader(object):
    def __init__(self):
        self._config = Config()

        if self._config.access_token is None:
            self._login_udemy()

        self._course_list: SubscribedCourseList | None = None

    def _login_udemy(self):
        print('Login...')
        response_get = requests.get(self._config.udemy_base_url)
        check_response(response_get)

        csrf_token = response_get.cookies.get('csrftoken')

        post_url = self._config.udemy_base_url + '/join/login-popup/?next=organization/home'
        payload = {
            'email': self._config.email,
            'password': self._config.password,
            'csrfmiddlewaretoken': csrf_token,
            'locale': 'ja_JP',
        }
        headers = {
            'Referer': self._config.udemy_base_url,
        }
        cookies = {
            'csrftoken': csrf_token,
            'ud_locale': 'ja_JP',
        }

        response_post = requests.post(post_url, data=payload, cookies=cookies, headers=headers)
        check_response(response_post)

        self._check_too_many_request_error(response_post)

        self._config.access_token = response_post.cookies.get('access_token')

    @staticmethod
    def _check_too_many_request_error(response: requests.Response):
        err = response.json().get('error')
        if err is not None:
            write_log(response)
            raise NeoUdelerError('Login failed:', err.get('data').get('errors').get('__all__'))

    def _is_authenticated(self) -> bool:
        return self._config.access_token is not None

    def fetch_subscribed_courses(self, search_keyword: str | None = None):
        if not self._is_authenticated():
            raise NeoUdelerError('Not Authenticated')

        api_path = '/api-2.0/users/me/subscribed-courses'
        params = {
            'page_size': 1000,
            'page': 1,
            'fields[course]': '',
            'fields[user]': '',
        }
        if search_keyword is not None:
            params['search'] = search_keyword

        response = requests.get(self._config.udemy_base_url + api_path,
                                params=params,
                                cookies={'access_token': self._config.access_token})
        check_response(response)

        json_data = response.json()

        count = json_data.get('count')
        results = json_data.get('results')
        courses = self._create_course_list(results)

        self._course_list = SubscribedCourseList(course_count=count, courses=courses, search_keyword=search_keyword)
        return self._course_list

    def _create_course_list(self, results: list[dict]) -> list[Course]:
        courses: list[Course] = []
        for result in results:
            visible_instructors = self._create_visible_instructors_list(result.get('visible_instructors'))

            courses.append(Course(
                course_id=result.get('id'),
                title=result.get('title'),
                url=self._config.udemy_base_url + result.get('url'),
                image_480_270_url=result.get('image_480x270'),
                locale_title=result.get('locale').get('title'),
                visible_instructors=visible_instructors,
            ))
        return courses

    def _create_visible_instructors_list(self, results: list[dict]) -> list[Instructor]:
        visible_instructors = []
        for result in results:
            visible_instructors.append(Instructor(
                user_id=result.get('id'),
                title=result.get('title'),
                name=result.get('name'),
                display_name=result.get('display_name'),
                job_title=result.get('job_title'),
                image_100_100=result.get('image_100x100'),
                user_url=self._config.udemy_base_url + result.get('url'),
            ))
        return visible_instructors
