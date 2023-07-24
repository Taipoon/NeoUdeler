import sys

import dotenv

from neoudeler import UdemyDownloader


def main():
    from colorama import Fore

    if not dotenv.get_key('.env', 'UDEMY_EMAIL') or not dotenv.get_key('.env', 'UDEMY_PASSWORD'):
        print(f'{Fore.RED}Set login email and password to .env file{Fore.RESET}')
        sys.exit(0)

    downloader = UdemyDownloader()

    sk = input('Search Keyword (input "all" to list up your subscribed courses): ').strip()
    sk = sk if sk != 'all' else None

    subscribed_courses = downloader.fetch_subscribed_courses(search_keyword=sk)

    if subscribed_courses.course_count == 0:
        print(f'{Fore.RED}Course not found{Fore.RESET}')
        sys.exit(0)

    for c in subscribed_courses.courses:
        print(f'{Fore.YELLOW}[{c.course_id}]{Fore.RESET}\t{c.title}')
    else:
        print(f'{Fore.YELLOW}[0]{Fore.RESET}\tCancel to download')

    cid = int(input(f'Select {Fore.YELLOW}[COURSE ID]{Fore.RESET} to download: '))
    if cid == 0:
        print('Bye!')
        sys.exit(0)

    course = subscribed_courses.find_course_by_course_id(course_id=cid)

    answer = input(f'Do you download {Fore.YELLOW}"{course.title}"{Fore.RESET}, are you sure? [y/N]: ').strip().lower()

    if answer not in ['y', 'yes']:
        print(f'{Fore.RED}Download is stopped{Fore.RESET}')
        sys.exit(0)

    # Download contents
    course.download_all_contents('.')


if __name__ == '__main__':
    main()
