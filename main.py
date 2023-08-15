import sys

import colorama
import dotenv
from colorama import Fore

from neoudeler import UdemyDownloader

colorama.init(autoreset=True)


def get_credentials_from_env():
    return dotenv.get_key('.env', 'UDEMY_EMAIL'), dotenv.get_key('.env', 'UDEMY_PASSWORD')


def prompt_for_search_keyword():
    return input('Search Keyword (input "all" to list up your subscribed courses): ').strip()


def display_courses(subscribed_courses):
    for course in subscribed_courses.courses:
        print(f'{Fore.YELLOW}[{course.course_id}]{Fore.RESET}\t{course.title}')
    print(f'{Fore.YELLOW}[0]{Fore.RESET}\tCancel to download')


def main():
    email, password = get_credentials_from_env()

    if not email or not password:
        print(f'{Fore.RED}Set login email and password to .env file{Fore.RESET}')
        sys.exit(0)

    downloader = UdemyDownloader()
    search_keyword = prompt_for_search_keyword()
    search_keyword = None if search_keyword == 'all' else search_keyword

    subscribed_courses = downloader.fetch_subscribed_courses(search_keyword=search_keyword)

    if subscribed_courses.course_count == 0:
        print(f'{Fore.RED}Course not found{Fore.RESET}')
        sys.exit(0)

    display_courses(subscribed_courses)

    course_id = int(input(f'Select {Fore.YELLOW}[COURSE ID]{Fore.RESET} to download: '))
    if course_id == 0:
        print('Bye!')
        sys.exit(0)

    course = subscribed_courses.find_course_by_course_id(course_id=course_id)
    answer = input(f'Do you download {Fore.YELLOW}"{course.title}"{Fore.RESET}, are you sure? [y/N]: ').strip().lower()

    if answer not in ['y', 'yes']:
        print(f'{Fore.RED}Download is stopped{Fore.RESET}')
        sys.exit(0)

    course.download_all_contents('.')


if __name__ == '__main__':
    main()
