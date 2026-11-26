# Как это работает

Документ объясняет, что происходит между `zapret` (или `zapret-flowseal`) и реальным обходом DPI в Linux.

## 1. Зачем вообще конвертация

Оригинальный [Flowseal/zapret-discord-youtube](https://github.com/Flowseal/zapret-discord-youtube) — Windows-проект:

- стратегии описаны в `general*.bat`;
- запускают `bin/winws2.exe`;
- перехват трафика делает WinDivert через опции `--wf-tcp-out` / `--wf-udp-out`;
- пути к спискам и Lua задаются переменными `%LISTS%`, `%LUA%`, `%BIN%`.

В Linux перехват делает `nfqws2` из [bol-van/zapret2](https://github.com/bol-van/zapret2) через **NFQUEUE + nftables**. У него другой движок, другой синтаксис запуска и другой init-скрипт. Поэтому `.bat` нельзя просто запустить — нужно перевести параметры.

Мы не пишем свои стратегии. Конвертер берёт готовую команду из каждого `general*.bat` и сохраняет её смысл: все `--lua-desync`, `--new`, `--template`, `--payload`, `--hostlist`, `--ipset`, `--filter-*` остаются как есть.

```
general (FAKE TLS AUTO).bat
        │
        │  flowseal_convert.py
        ▼
--chdir=/opt/zapret2
--debug=0
--blob=zero4:0x00000000
--lua-init=@/opt/zapret2/lua/blobs.lua
--filter-tcp=443
--hostlist=/opt/zapret2/flowseal/assets/lists/list-general.txt
--lua-desync=fake:blob=tls_clienthello_google:repeats=6
...
        │
        ▼
NFQWS2_OPT в /opt/zapret2/config
```

## 2. Версия движка

`winws2.exe` из Flowseal содержит строку `v1.0.7`. Это версия zapret2, под которую написаны его Lua-скрипты (`NFQWS2_COMPAT_VER_REQUIRED=6`).

При `install` адаптер:

1. ищет `vX.Y.Z` в `strings bin/winws2.exe`;
2. клонирует `bol-van/zapret2` с тегом этой версии (по умолчанию `v1.0.7`);
3. собирает `nfqws2` через `make` (нужны `libnetfilter_queue` и Lua).

⚠️ Lua-файлы из разных релизов zapret2 несовместимы. Поэтому если Flowseal обновит бинарник, адаптер предупредит; обновлять движок нужно **`zapret update --engine`**, а не просто `git pull` в `/opt/zapret2`.

## 3. Что именно делает конвертер

Файл: `flowseal_convert.py`.

| Преобразование | Пример | Причина |
| --- | --- | --- |
| Склейка `^`-продолжений bat | `--new ^` + пустая строка + `--lua-desync=...` → одна строка | В `.bat` логический блок разбит пустыми строками после `^` |
| Удаление WinDivert-опций | `--wf-tcp-out=...`, `--wf-udp-out=...` | В Linux их заменяют `NFQWS2_PORTS_TCP/UDP` + nftables |
| Подстановка `%LUA%` | `--lua-init=@"%LUA%blobs.lua"` → `--lua-init=@/opt/zapret2/lua/blobs.lua` | Абсолютный путь надёжнее |
| Подстановка `%LISTS%` | `--hostlist="%LISTS%list-general.txt"` → `--hostlist=/opt/zapret2/flowseal/assets/lists/list-general.txt` | Списки хранятся отдельно от движка |
| Подстановка `%BIN%` | `%BIN%` → `/opt/zapret2/bin/` | Оттуда `blobs.lua` грузит `*.bin` |
| `%GameFilterTCP/UDP%` | `12` (выключено) или `1024-65535` | У Flowseal `12` — инертный плейсхолдер, когда фильтр игр выключен |
| Пропуск дублей Lua | `--lua-init=@…/zapret-lib.lua`, `zapret-antidpi.lua` удаляются | Их уже грузит init-скрипт zapret2 (см. ниже) |
| `--name="Domain Quic"` | `--name=Domain_Quic` | `NFQWS2_OPT` раскрывается shell'ом без кавычек; это лишь метка в логах |
| Добавление `--chdir` | `--chdir=/opt/zapret2` в начало | `blobs.lua` ищет `bin/*.bin` относительно cwd |

Всё остальное (`--lua-desync`, `--payload`, `--template`, `--new`, `--hostlist-exclude`, `--ipset`, `--filter-l7` и т.д.) переносится без изменений.

Проверка: количество ключевых опций (`--new`, `--lua-desync`, `--filter-tcp`, `--filter-udp`) в каждом сконвертированном файле совпадает с исходным `.bat` — это тестируется для всех 22 стратегий.

## 4. Почему нельзя положить стратегию в `@file`

`nfqws2` поддерживает `--@config_file`, но при использовании `@file` остальные CLI-опции игнорируются. Init-скрипт zapret2 сам добавляет `--qnum`, `--user`, `--fwmark`, `--lua-init`, поэтому стратегия должна быть **inline** в `NFQWS2_OPT`.

Для этого вместо одного `--@generated/general.conf` в конфиг пишется многострочное значение:

```sh
NFQWS2_OPT="
--chdir=/opt/zapret2
--debug=0
--lua-init=@/opt/zapret2/lua/blobs.lua
...
"
```

Каждая опция — на отдельной строке, без пробелов внутри (поэтому `--name` и нормализуется).

## 5. Как устроен `/opt/zapret2/config`

Адаптер не перезаписывает `config.default` целиком. Он берёт существующий `config` (или `config.default`) и заменяет только блок между маркерами:

```sh
# >>> zapret-flowseal managed settings
ZAPRET_BASE=/opt/zapret2
DESYNC_MARK=0x40000000
DESYNC_MARK_POSTNAT=0x20000000
NFQWS2_ENABLE=1
NFQWS2_PORTS_TCP=80,443,2053,2083,2087,2096,8443
NFQWS2_PORTS_UDP=443,19294-19344,50000-50100
NFQWS2_TCP_PKT_OUT=20
NFQWS2_TCP_PKT_IN=10
NFQWS2_UDP_PKT_OUT=5
NFQWS2_UDP_PKT_IN=3
MODE_FILTER=none
FLOWOFFLOAD=donttouch
INIT_APPLY_FW=1
DISABLE_IPV6=1
NFQWS2_OPT="
... стратегия Flowseal ...
"
# <<< zapret-flowseal managed settings
```

Остальные пользовательские настройки файла сохраняются.

### Порты

Порты берутся из `--filter-tcp` / `--filter-udp` и `--wf-*` всех стратегий Flowseal:

- TCP: `80,443,2053,2083,2087,2096,8443`
- UDP: `443,19294-19344,50000-50100`

Если включить `zapret game-filter all`, добавляется `1024-65535` — ровно тот диапазон, который использует `GameFilter` в `service.bat`.

### Фильтрация

`MODE_FILTER=none`: nftables перенаправляет **все** пакеты на перечисленные порты в NFQUEUE, а решение «трогать или нет» принимает `nfqws2` внутри стратегии через `--hostlist`, `--hostlist-exclude`, `--ipset`, `--ipset-exclude`. Так же работает оригинал на Windows.

## 6. Что происходит при `zapret start`

`zapret start` → `service_action()` → родной скрипт `/opt/zapret2/init.d/sysv/zapret2 start` → `init.d/sysv/functions` → `common/linux_daemons.sh`.

Итоговая команда выглядит так:

```
nfqws2 \
  --user=tpws \
  --fwmark=0x40000000 \
  --lua-init=@/opt/zapret2/lua/zapret-lib.lua \
  --lua-init=@/opt/zapret2/lua/zapret-antidpi.lua \
  --lua-init=@/opt/zapret2/lua/zapret-auto.lua \
  --qnum=300 \
  <NFQWS2_OPT из стратегии Flowseal>
```

Отсюда два важных следствия:

1. **Нельзя дублировать `zapret-lib.lua` и `zapret-antidpi.lua` в стратегии** — конвертер их пропускает.
2. `zapret-auto.lua` остаётся от движка v1.0.7. Он совместим, потому что Lua-файлы Flowseal после нормализации CRLF **побайтово совпадают** с lua-файлами zapret2 v1.0.7.

Плюс init-скрипт создаёт таблицу nftables `inet zapret2` с правилами NFQUEUE, учитывая `NFQWS2_PORTS_TCP/UDP`, `DESYNC_MARK` и `INIT_APPLY_FW=1`.

## 7. Синхронизация с upstream

Команда `zapret update` (и systemd-таймер) выполняет:

```
git fetch origin main
        │
        ├─ commit не изменился → выход (никаких перезапусков)
        │
        └─ изменился ↓
             reset --hard FETCH_HEAD
             копирование lists/ → /opt/zapret2/flowseal/assets/lists
             копирование lua/*.lua → /opt/zapret2/lua   (CRLF → LF)
             копирование bin/*.bin → /opt/zapret2/bin
             .service/ipset-service.txt → lists/ipset-all.txt
             перегенерация всех 22 generated/*.conf
             перезапись NFQWS2_OPT в /opt/zapret2/config
             сравнение хешей активной стратегии
                    │
                    ├─ изменилась + zapret запущен → restart
                    └─ изменилась + выключен → сообщение в лог
```

Детали:

- `lists/*-user.txt` **никогда не перезаписываются** — это ваши домены/IP, как в оригинале.
- `ipset-all.txt` в репозитории Flowseal — заглушка `203.0.113.113/32`; настоящий список лежит в `.service/ipset-service.txt`. Адаптер делает то же, что кнопка «Update IPSet List» в `service.bat`.
- Все операции защищены `flock` (`update.lock`), чтобы таймер и ручной `update` не конфликтовали.
- Результат сохраняется в `state.json`: commit, версия Flowseal, версия движка, SHA256 каждой стратегии, время синхронизации.

### Автообновление

`zapret auto-update on` включает `zapret-flowseal-update.timer`:

```ini
OnBootSec=3min
OnCalendar=daily
Persistent=true
RandomizedDelaySec=15min
```

`Persistent=true` означает: если машина была выключена в момент срабатывания, проверка выполнится при следующей загрузке. Логи смотрим так:

```bash
journalctl -u zapret-flowseal-update.service -f
```

Без systemd — `zapret watch --interval 3600` или cron:

```
0 6 * * * /opt/zapret2/flowseal/tool/zapret-flowseal update --auto
```

## 8. Автозапуск

`zapret autostart on` включает `zapret-flowseal.service`:

```ini
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/opt/zapret2/init.d/sysv/zapret2 start
ExecStop=/opt/zapret2/init.d/sysv/zapret2 stop
```

То есть systemd не придумывает свой способ запуска — он просто вызывает родной init-скрипт zapret2. Порядок: сначала сеть (`After=network-online.target`), затем zapret. Автообновление и автозапуск — независимые переключатели.

## 9. Как выбирается «лучшая стратегия»

`zapret best` — порт `utils/test zapret.ps1` от Flowseal.

1. Берутся цели из `utils/targets.txt` upstream (Discord, YouTube, Google, Cloudflare + 4 public DNS на ping).
2. Для каждой из 22 стратегий по очереди:
   - `stop` → записать `NFQWS2_OPT` → `start`;
   - дождаться pid-файла `/var/run/nfqws2_1.pid`;
   - параллельно (`--workers`, по умолчанию 12) выполнить для каждого URL три проверки: `curl -I --http1.1`, `curl -I --tlsv1.2`, `curl -I --tlsv1.3`; отдельно `ping -c 1`;
   - посчитать `OK` (успешные HTTP/TLS), `ping OK`, `errors` (SSL/timeout/ошибка).
3. В конце всё останавливается, активная стратегия восстанавливается.
4. Стратегии сортируются по `(OK, ping OK)`; показывается таблица и сохраняется отчёт.
5. С `--apply` лучшая стратегия становится активной; с `--start` — ещё и запускается.

Ограничение теста: он измеряет доступность целей **в данный момент и на этом провайдере**. Результат не является универсальной истиной — провайдеры и регионы блокируют по-разному. Поэтому отчёт можно перезапустить позже: `zapret best --apply --start`.

## 10. Меню и одна команда

`zapret` — bash-wrapper:

- ищет `zapret-flowseal` рядом с собой, затем в `/opt/zapret2/flowseal/tool`, затем в `~/Projects/zapret-flowseal-linux`;
- если пользователь не root, один раз вызывает `sudo -E python3 …` (один запрос пароля на всё меню);
- без аргументов открывает `cmd_menu()`, с аргументами — сразу выполняет команду.

Меню просто переиспользует те же функции CLI через `invoke()`; никакой второй бизнес-логики нет.

## 11. Куда смотреть при проблемах

| Симптом | Что делать |
| --- | --- |
| `error: not installed` | `sudo bash install-here.sh` |
| Сборка `nfqws2` падает | доставить `libnetfilter_queue` + Lua dev; `zapret diagnostics` |
| `nfqws2 --dry-run: FAILED` | `zapret check`, проверить пути в `NFQWS2_OPT` |
| Сервис не стартует | `journalctl -u zapret-flowseal.service`, `zapret diagnostics` |
| Нет эффекта в браузере | Secure DNS включён? `zapret best --apply --start` |
| Обновился upstream, но стратегию не видим | `zapret update`, затем `zapret list` |
| Flowseal обновил бинарник | `zapret update --engine` |

## 12. Ключевые файлы

| Файл | Роль |
| --- | --- |
| `zapret-flowseal` | весь CLI, меню, sync/update, systemd, best-тест |
| `flowseal_convert.py` | чистый конвертер `.bat` → список аргументов |
| `zapret` | однокомандный wrapper с sudo |
| `install-here.sh` | установка зависимостей + `install` |
| `tests/test_convert.py` | тесты конвертации, в т.ч. всех стратегий upstream |
| `tests/test_cli.py` | тесты CLI и разбора `targets.txt` |
