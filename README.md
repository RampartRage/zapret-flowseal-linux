# zapret-flowseal

Консольная адаптация [Flowseal/zapret-discord-youtube](https://github.com/Flowseal/zapret-discord-youtube) для Linux: те же самые стратегии, но через `nfqws2` из [bol-van/zapret2](https://github.com/bol-van/zapret2), с консольным менеджером, автообновлением конфигов из upstream и автозапуском.

> **Принцип:** ни одной своей стратегии. Все 22 `general*.bat` конвертируются один-в-один; удаляются только Windows-специфичные опции.

Запуск одной командой:

```bash
zapret
```

---

## Возможности

| Что | Как |
| --- | --- |
| Стратегии | Все `general*.bat` из репозитория Flowseal (22 на момент v1.10.4) |
| Движок | zapret2 **v1.0.7** — версия из `bin/winws2.exe` Flowseal, определяется автоматически |
| Конвертация | `%LUA%`, `%LISTS%`, `%BIN%`, `%GameFilter*` подставляются; `--wf-*` удаляются |
| Обновление | `git fetch` upstream → перегенерация всех конфигов → reload активной стратегии |
| Автозапуск | systemd-юнит `zapret-flowseal.service` (`zapret autostart on`) |
| Автообновление | `zapret-flowseal-update.timer`, раз в сутки (`zapret auto-update on`) |
| Выбор лучшей | `zapret best` — адаптация `utils/test zapret.ps1` автора |
| Меню | Цветной интерактивный интерфейс в стиле `service.bat` |
| Диагностика | `zapret diagnostics`, `zapret check` (dry-run nfqws2) |

---

## Установка

Требования: Linux с `nftables`, root, `git`, `curl`, `gcc`, `make`, `nft`, `python3` 3.9+, заголовки `libnetfilter_queue` и Lua.

```bash
git clone https://github.com/RampartRage/zapret-flowseal-linux.git
cd zapret-flowseal-linux
sudo bash install-here.sh
```

`install-here.sh` поставит недостающие dev-пакеты (Arch: `libnetfilter_queue luajit`; Debian/Ubuntu: `libnetfilter-queue-dev liblua5.1-0-dev`) и вызовет `zapret-flowseal install`.

Установка не включает автозапуск и таймер обновления автоматически. После установки:

```bash
zapret autostart on     # включить демон и запустить его сейчас
zapret auto-update on   # опционально: проверять upstream раз в сутки
```

Повторный `install` сохраняет пользовательские `*-user.txt` и не удаляет чужие данные: если `/opt/zapret2` уже есть, но не является репозиторием zapret2, он переносится в `/opt/zapret2.backup-<дата>`.

Если зависимости уже есть:

```bash
sudo python3 zapret-flowseal install
sudo python3 zapret-flowseal install --strategy 'general (FAKE TLS AUTO)'
```

### Что появляется после установки

| Путь | Назначение |
| --- | --- |
| `/opt/zapret2` | движок zapret2 + родные `init.d/sysv/zapret2` |
| `/opt/zapret2/flowseal/upstream` | клон Flowseal — единственный источник стратегий |
| `/opt/zapret2/flowseal/assets/lists` | списки Flowseal + пользовательские `*-user.txt` |
| `/opt/zapret2/flowseal/generated/*.conf` | все 22 сконвертированные стратегии |
| `/opt/zapret2/flowseal/test-results/` | отчёты `zapret best` |
| `/opt/zapret2/flowseal/state.json` | последний commit, версия, хеши стратегий |
| `/etc/zapret-flowseal/config.json` | настройки адаптера |
| `/opt/zapret2/config` | активная стратегия в формате zapret2 (`ZAPRET_CONFIG` в init-скрипте) |
| `/usr/local/bin/zapret`, `/usr/local/bin/zapret-flowseal` | команды CLI |
| `/etc/systemd/system/zapret-flowseal*` | сервис, юнит и таймер обновления |

---

## Использование

### Меню

```bash
zapret
```

```
  ╔════════════════════════════════════════════════════════╗
  ║ ██  ЗАПРЕТ · FLOWSEAL   консольный менеджер            ║
  ╠════════════════════════════════════════════════════════╣
  ║   Стратегия      : general (FAKE TLS AUTO)             ║
  ║   Демон          : [ ОСТАНОВЛЕН ]                      ║
  ║   Автозапуск     : [ ВЫКЛЮЧЕН ]                        ║
  ║   Автообновление : [ ВЫКЛЮЧЕН ]                        ║
  ║   Фильтр игр     : выключен                            ║
  ║   Flowseal       : v1.10.4  a1b2c3d4                   ║
  ╠════════════════════════════════════════════════════════╣
  ║   СЛУЖБА                                               ║
  ║     1   Установить / переустановить                    ║
  ║     2   Включить автозапуск и запустить                ║
  ║     3   Выключить автозапуск и остановить              ║
  ║     4   Подробный статус                               ║
  ╠════════════════════════════════════════════════════════╣
  ║   СТРАТЕГИИ                                            ║
  ║     5   Выбрать стратегию                              ║
  ║     6 ★ Найти лучшую стратегию (автотест)              ║
  ║     7   Фильтр игр                                     ║
  ╠════════════════════════════════════════════════════════╣
  ║   ОБНОВЛЕНИЯ                                           ║
  ║     8   Обновить конфиги сейчас                        ║
  ║     9   Автообновление: включить / выключить           ║
  ║    10   Обновить движок zapret2                        ║
  ╠════════════════════════════════════════════════════════╣
  ║   ИНСТРУМЕНТЫ                                          ║
  ║    11   Диагностика системы                            ║
  ║    12   Проверка конфигурации (dry-run)                ║
  ╚════════════════════════════════════════════════════════╝

  Подсказка: включите Secure DNS в браузере / ОС
  Действия требуют root — пароль запрашивается один раз

  0 — выход

  Ваш выбор:
```

Весь интерфейс на русском: рамки, цветные бейджи `[ ЗАПУЩЕН ]` / `[ ОСТАНОВЛЕН ]`, подсветка активной стратегии звёздочкой и подсказки. Цвета автоматически отключаются, если вывод не в терминале или задан `NO_COLOR`.

Пункт 6 перебирает все стратегии, тестирует цели из `utils/targets.txt` и предлагает применить лучшую.

### CLI

```bash
zapret list                                     # список стратегий
zapret use 19                                   # выбрать номером
zapret use 'general (SIMPLE FAKE)'              # выбрать именем
zapret start | stop | restart | status
zapret check                                    # валидация + nfqws2 --dry-run
zapret diagnostics                              # проверка установки
zapret game-filter off|tcp|udp|all
zapret best                                     # автотест всех стратегий
zapret best --apply --start                     # применить лучшую и запустить
zapret best --limit 5 --timeout 3 --workers 16  # быстрый тест
zapret autostart on|off|status                  # запуск при загрузке
zapret auto-update on|off|status                # обновление конфигов
zapret update                                   # обновиться сейчас
zapret update --engine                          # + обновить движок
zapret watch --interval 3600                    # polling без systemd
zapret uninstall [--purge]
```

Полный справочник — [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md).

---

## Как это работает

Подробный разбор с диаграммами, таблицей преобразований, устройством `/opt/zapret2/config`, алгоритмами обновления и теста — в **[docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md)**.

Кратко:

```
Flowseal (GitHub) ──git fetch──> upstream/
                                   │
                    general*.bat ──┤ конвертер
                    lists/, lua/, bin/*.bin
                                   ▼
                    generated/*.conf + /opt/zapret2/config
                                   ▼
                    init.d/sysv/zapret2 start ──> nfqws2 + nftables
                                   ▲
                    zapret (меню / CLI / systemd)
```

---

## Тесты

```bash
python3 -m unittest discover -s tests -v
FLOWSEAL_UPSTREAM=/path/to/zapret-discord-youtube python3 -m unittest discover -s tests -v
```

Второй вариант проверяет конвертацию всех реальных стратегий upstream. Сейчас 13 тестов.

---

## Ограничения

- NFQUEUE и nftables требуют root.
- `blobs.lua` ищет `.bin` относительно cwd — поэтому в стратегии добавляется `--chdir=/opt/zapret2`.
- Если автор добавит новую Windows-опцию, `zapret check` покажет её; конвертер удаляет только `--wf-*`.
- Secure DNS в браузере/ОС обязателен, как и в оригинальной инструкции Flowseal.
- Проект не обходит Spotify и не чинит веб-Telegram — как и оригинал.

---

## Лицензия и благодарности

Код адаптера — MIT, см. [LICENSE](LICENSE). Конфигурации, списки, Lua-скрипты и бинарники fake-payload принадлежат авторам original-проектов: [Flowseal](https://github.com/Flowseal/zapret-discord-youtube) и [bol-van](https://github.com/bol-van/zapret2). См. [NOTICE](NOTICE).
