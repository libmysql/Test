#!/usr/bin/env python3
import os
import sys
import time
import requests
import json
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
import socket
import whois
import dns.resolver
from colorama import Fore, Back, Style, init
import re
from bs4 import BeautifulSoup
import urllib.parse

# Инициализация colorama
init(autoreset=True)

# Проверка на Termux
TERMUX = True if "com.termux" in os.getenv('PATH', '') else False

# ASCII Арт и баннер
BANNER = f"""
{Fore.RED}╦  ╦┬┌─┐┌─┐┬ ┬  {Fore.YELLOW}┬  ┬┌─┐┌┬┐┌─┐┬─┐
{Fore.RED}╚╗╔╝│├┤ │  ├─┤  {Fore.YELLOW}└┐┌┘├┤ │││├┤ ├┬┘
{Fore.RED} ╚╝ ┴└─┘└─┘┴ ┴  {Fore.YELLOW} └┘ └─┘┴ ┴└─┘┴└─
{Fore.CYAN}════════════════════════════════════
{Fore.GREEN}  libmyINT - Продвинутый 0sint инструмент
{Fore.CYAN}════════════════════════════════════
{Style.RESET_ALL}
"""

# Главное меню
MAIN_MENU = f"""
{Fore.YELLOW}1.{Fore.WHITE} Поиск по IP
{Fore.YELLOW}2.{Fore.WHITE} Поиск по номеру телефона
{Fore.YELLOW}3.{Fore.WHITE} Поиск по email
{Fore.YELLOW}4.{Fore.WHITE} Анализ домена
{Fore.YELLOW}5.{Fore.WHITE} Поиск по никнейму
{Fore.YELLOW}6.{Fore.WHITE} Поиск ФИО/личных данных
{Fore.YELLOW}7.{Fore.WHITE} Проверка соц. сетей
{Fore.YELLOW}8.{Fore.WHITE} Проверка на утечки
{Fore.YELLOW}9.{Fore.WHITE} О программе
{Fore.RED}0.{Fore.WHITE} Выход
"""

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def print_slow(text):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.002)
    print()

def display_banner():
    clear_screen()
    print_slow(BANNER)

def get_phone_info(phone_number):
    """Получение информации о номере телефона с поиском ФИО"""
    try:
        # Парсинг номера
        parsed_num = phonenumbers.parse(phone_number, None)
        
        # Базовая информация
        info = {
            "Номер": phonenumbers.format_number(parsed_num, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            "Страна": geocoder.description_for_number(parsed_num, "ru"),
            "Оператор": carrier.name_for_number(parsed_num, "ru"),
            "Часовой пояс": timezone.time_zones_for_number(parsed_num),
            "Действительный": "Да" if phonenumbers.is_valid_number(parsed_num) else "Нет"
        }
        
        # Поиск ФИО через бесплатные источники
        try:
            # Используем API numverify (бесплатный тариф)
            response = requests.get(f"http://apilayer.net/api/validate?access_key=free&number={phone_number}&format=1")
            if response.status_code == 200:
                data = response.json()
                if 'valid' in data and data['valid']:
                    info.update({
                        "Формат": data.get('local_format'),
                        "Тип линии": data.get('line_type'),
                        "Местоположение": data.get('location')
                    })
        except:
            pass
            
        # Дополнительные проверки для российских номеров
        if info["Страна"] == "Россия":
            try:
                # Проверка через сервисы подбора (используем только открытые данные)
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                # 1. Поиск через sberbank (пример)
                try:
                    sber_url = f"https://sberbank.ru/phone-search?phone={phone_number[-10:]}"
                    response = requests.get(sber_url, headers=headers, timeout=5)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        name_tag = soup.find('div', class_='user-name')
                        if name_tag:
                            info["Имя (Sber)"] = name_tag.text.strip()
                except:
                    pass
                
                # 2. Поиск через avito (пример)
                try:
                    avito_url = f"https://www.avito.ru/items/phone/{phone_number[-10:]}"
                    response = requests.get(avito_url, headers=headers, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if 'name' in data:
                            info["Имя (Avito)"] = data['name']
                except:
                    pass
                
                # 3. Поиск через бесплатные API
                try:
                    response = requests.get(f"https://phoneinfoga.crvx.fr/api/numbers/{phone_number}/scan/numverify")
                    if response.status_code == 200:
                        data = response.json()
                        if 'name' in data:
                            info["Имя (Numverify)"] = data['name']
                except:
                    pass
                
            except Exception as e:
                info["Ошибка доп. проверки"] = str(e)
        
        return info
        
    except Exception as e:
        return {"Ошибка": str(e)}

def get_ip_info(ip):
    """Получение информации об IP адресе"""
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?lang=ru").json()
        
        return {
            "IP": ip,
            "Страна": response.get('country', 'Неизвестно'),
            "Регион": response.get('regionName', 'Неизвестно'),
            "Город": response.get('city', 'Неизвестно'),
            "Интернет-провайдер": response.get('isp', 'Неизвестно'),
            "Организация": response.get('org', 'Неизвестно'),
            "Координаты": f"{response.get('lat', '?')}, {response.get('lon', '?')}",
            "Почтовый индекс": response.get('zip', 'Неизвестно'),
            "Часовой пояс": response.get('timezone', 'Неизвестно')
        }
    except Exception as e:
        return {"Ошибка": str(e)}

def email_investigation(email):
    """Исследование email адреса"""
    try:
        # Проверка через haveibeenpwned (бесплатно)
        breaches = []
        try:
            response = requests.get(f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}", 
                                  headers={"User-Agent": "libmyINT"})
            if response.status_code == 200:
                breaches = json.loads(response.text)
        except:
            pass
            
        # Проверка через weleakinfo (альтернатива)
        leaks = []
        try:
            response = requests.get(f"https://api.weleakinfo.com/v3/public/email/{email}",
                                 headers={"Authorization": "free"})
            if response.status_code == 200:
                leaks = response.json().get('data', [])
        except:
            pass
            
        return {
            "Утечки данных (HIBP)": breaches if breaches else "Не найдено",
            "Утечки данных (WeLeakInfo)": leaks if leaks else "Не найдено",
            "Домен": email.split('@')[-1]
        }
    except Exception as e:
        return {"Ошибка": str(e)}

def domain_analysis(domain):
    """Анализ домена"""
    try:
        # WHOIS информация
        domain_info = whois.whois(domain)
        
        # DNS записи
        dns_records = {}
        for record in ['A', 'MX', 'NS', 'TXT']:
            try:
                answers = dns.resolver.resolve(domain, record)
                dns_records[record] = [str(r) for r in answers]
            except:
                pass
                
        return {
            "WHOIS": {
                "Регистратор": domain_info.registrar,
                "Дата создания": domain_info.creation_date,
                "Дата окончания": domain_info.expiration_date,
                "NS серверы": domain_info.name_servers
            },
            "DNS записи": dns_records
        }
    except Exception as e:
        return {"Ошибка": str(e)}

def username_search(username):
    """Поиск по никнейму"""
    sites = {
        "ВКонтакте": f"https://vk.com/{username}",
        "Одноклассники": f"https://ok.ru/{username}",
        "Telegram": f"https://t.me/{username}",
        "GitHub": f"https://github.com/{username}",
        "Instagram": f"https://instagram.com/{username}",
        "Twitter": f"https://twitter.com/{username}"
    }
    
    results = {}
    for site, url in sites.items():
        try:
            response = requests.head(url, timeout=5)
            if response.status_code == 200:
                results[site] = url
        except:
            pass
            
    return results if results else {"Результаты": "Не найдено"}

def personal_info_search(query):
    """Поиск личной информации"""
    search_urls = {
        "Google": f"https://www.google.com/search?q={urllib.parse.quote(query)}",
        "Яндекс": f"https://yandex.ru/search/?text={urllib.parse.quote(query)}",
        "Mail.ru": f"https://go.mail.ru/search?q={urllib.parse.quote(query)}"
    }
    
    return search_urls

def print_result(title, data):
    """Вывод результатов"""
    print(f"\n{Fore.CYAN}════════════ {Fore.YELLOW}{title}{Fore.CYAN} ════════════{Style.RESET_ALL}\n")
    
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                print(f"{Fore.GREEN}{key}:{Style.RESET_ALL}")
                print(json.dumps(value, indent=2, ensure_ascii=False))
            else:
                print(f"{Fore.GREEN}{key}:{Style.RESET_ALL} {value}")
    else:
        print(data)
        
    print(f"\n{Fore.CYAN}════════════════════════════════════════════{Style.RESET_ALL}\n")

def main():
    display_banner()
    
    while True:
        print(MAIN_MENU)
        choice = input(f"{Fore.YELLOW}libmyINT>{Style.RESET_ALL} ").strip()
        
        if choice == "1":  # Поиск по IP
            ip = input("Введите IP адрес: ").strip()
            if ip:
                result = get_ip_info(ip)
                print_result("Результаты поиска по IP", result)
            else:
                print(f"{Fore.RED}Введите корректный IP адрес{Style.RESET_ALL}")
                
        elif choice == "2":  # Поиск по номеру
            phone = input("Введите номер телефона (с кодом страны): ").strip()
            if phone:
                result = get_phone_info(phone)
                print_result("Результаты поиска по номеру", result)
            else:
                print(f"{Fore.RED}Введите корректный номер телефона{Style.RESET_ALL}")
                
        elif choice == "3":  # Поиск по email
            email = input("Введите email адрес: ").strip()
            if "@" in email:
                result = email_investigation(email)
                print_result("Результаты поиска по email", result)
            else:
                print(f"{Fore.RED}Введите корректный email адрес{Style.RESET_ALL}")
                
        elif choice == "4":  # Анализ домена
            domain = input("Введите домен (без http://): ").strip()
            if "." in domain:
                result = domain_analysis(domain)
                print_result("Результаты анализа домена", result)
            else:
                print(f"{Fore.RED}Введите корректный домен{Style.RESET_ALL}")
                
        elif choice == "5":  # Поиск по никнейму
            username = input("Введите никнейм: ").strip()
            if username:
                result = username_search(username)
                print_result("Результаты поиска по никнейму", result)
            else:
                print(f"{Fore.RED}Введите никнейм{Style.RESET_ALL}")
                
        elif choice == "6":  # Поиск личной информации
            query = input("Введите ФИО/другие данные: ").strip()
            if query:
                result = personal_info_search(query)
                print_result("Результаты поиска", result)
            else:
                print(f"{Fore.RED}Введите данные для поиска{Style.RESET_ALL}")
                
        elif choice == "7":  # Проверка соц. сетей
            username = input("Введите никнейм: ").strip()
            if username:
                result = username_search(username)
                print_result("Наличие в соц. сетях", result)
            else:
                print(f"{Fore.RED}Введите никнейм{Style.RESET_ALL}")
                
        elif choice == "8":  # Проверка на утечки
            email = input("Введите email: ").strip()
            if "@" in email:
                result = email_investigation(email)
                print_result("Проверка на утечки данных", result)
            else:
                print(f"{Fore.RED}Введите корректный email{Style.RESET_ALL}")
                
        elif choice == "9":  # О программе
            print(f"""
{Fore.CYAN}════════════ О программе ════════════{Style.RESET_ALL}

{Fore.YELLOW}libmyINT{Style.RESET_ALL} - мощный инструмент для OSINT исследований

{Fore.GREEN}Возможности:{Style.RESET_ALL}
- Поиск информации по номеру телефона (включая возможные ФИО)
- Геолокация по IP адресу
- Проверка email на участие в утечках данных
- Анализ доменов и WHOIS информация
- Поиск аккаунтов по никнейму
- Поиск личной информации в открытых источниках

{Fore.RED}Важно:{Style.RESET_ALL}
Используйте только для законных целей. 
Некоторые функции могут быть ограничены бесплатными API.

Нажмите Enter для возврата в меню...
""")
            input()
            display_banner()
            
        elif choice == "0":  # Выход
            print(f"\n{Fore.YELLOW}Спасибо за использование libmyINT!{Style.RESET_ALL}\n")
            sys.exit(0)
            
        else:
            print(f"{Fore.RED}Неверный выбор. Попробуйте снова.{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        # Проверка зависимостей
        required = ['requests', 'phonenumbers', 'python-whois', 'dnspython', 'colorama', 'bs4']
        
        missing = []
        for module in required:
            try:
                __import__(module)
            except ImportError:
                missing.append(module)
                
        if missing:
            print(f"{Fore.RED}Отсутствуют зависимости:{Style.RESET_ALL} {', '.join(missing)}")
            if TERMUX:
                print("Выполните: pip install " + " ".join(missing))
            sys.exit(1)
            
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Операция отменена пользователем.{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}Ошибка: {e}{Style.RESET_ALL}")
        sys.exit(1)
