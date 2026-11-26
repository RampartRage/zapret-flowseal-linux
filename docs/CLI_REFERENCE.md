# Справочник CLI

Все команды доступны через `zapret ...` и через `sudo zapret-flowseal ...`. Команды, меняющие состояние, требуют root; `zapret`-wrapper запрашивает sudo один раз при запуске.

## Команды

| Команда | Что делает | Root |
| --- | --- | --- |
| `zapret` (без аргументов) | Открывает интерактивное меню | да (через wrapper) |
| `menu` | То же, что без аргументов | да |
| `install [--strategy NAME]` | Клонирует/обновляет upstream и zapret2, собирает `nfqws2`, генерирует конфиги, ставит юниты и symlink'и | да |
| `list` | Показывает все стратегии Flowseal с номерами и активную | нет |
| `use NAME` / `use N` | Выбирает стратегию по имени или номеру из `list`; если zapret запущен — restart | да |
| `start` / `stop` / `restart` | Вызывает родной `/opt/zapret2/init.d/sysv/zapret2` | да |
| `status` | Активная стратегия, версии, commit, состояние демона, auto-update | нет |
| `check` | Проверяет конвертацию всех стратегий и делает `nfqws2 --dry-run` | нет |
| `diagnostics` | Проверяет файлы, бинарник, Lua, блобы, curl/ping, nftables | нет |
| `best [OPTIONS]` | Тестирует стратегии и находит лучшую | да |
| `game-filter MODE [--tcp ...] [--udp ...]` | Включает/выключает обработку игрового трафика | да |
| `update [--force] [--engine] [--auto]` | Синхронизирует конфиги с upstream | да |
| `auto-update on\|off\|status` | Управляет systemd-таймером обновления | да |
| `autostart on\|off\|status` | Управляет systemd-сервисом (запуск при загрузке) | да |
| `watch --interval N` | Постоянный polling upstream вместо systemd-таймера | да |
| `uninstall [--purge]` | Удаляет юниты и symlink'и; `--purge` — ещё и все данные | да |

## `best` — подробнее

```
zapret best [--apply] [--start] [--limit N] [--timeout SEC] [--workers N]
```

| Флаг | По умолчанию | Смысл |
| --- | --- | --- |
| `--apply` | выкл. | Применить лучшую стратегию после теста |
| `--start` | выкл. | Запустить zapret после `--apply` |
| `--limit N` | все | Протестировать только первые N стратегий (быстрая проверка) |
| `--timeout SEC` | `5` | Таймаут одного curl-запроса |
| `--workers N` | `12` | Сколько проверок выполнять параллельно |

Примеры:

```bash
zapret best                                     # полный прогон, только отчёт
zapret best --apply --start                     # найти, применить и запустить
zapret best --limit 5 --timeout 3 --workers 16  # черновой прогон
```

Отчёт сохраняется в `/opt/zapret2/flowseal/test-results/<дата>.txt`.

## `game-filter`

```
zapret game-filter off|tcp|udp|all [--tcp 1024-65535] [--udp 1024-65535]
```

| Режим | `%GameFilterTCP%` | `%GameFilterUDP%` |
| --- | --- | --- |
| `off` (по умолчанию) | `12` | `12` |
| `tcp` | `1024-65535` | `12` |
| `udp` | `12` | `1024-65535` |
| `all` | `1024-65535` | `1024-65535` |

Значение `12` — инертный плейсхолдер из `service.bat` Flowseal: порт почти никогда не используется, стратегия для него просто не срабатывает.

## `update`

```
zapret update [--force] [--engine] [--auto]
```

- `--force` — перегенерировать конфиги, даже если commit не изменился.
- `--engine` — если Flowseal поменял версию `winws2.exe`, обновить zapret2 до нового тега и пересобрать.
- `--auto` — режим для systemd-таймера (используется внутренне).

Если изменилась активная стратегия и zapret сейчас запущен — делается `restart`. Если не запущен — в лог пишется, что нужно запустить вручную.

## Переменные окружения

| Переменная | Назначение |
| --- | --- |
| `ZAPRET_FLOWSEAL_CONFIG` | Альтернативный путь к `config.json` (по умолчанию `/etc/zapret-flowseal/config.json`) |
| `NO_COLOR` | Отключает цвет в меню и логах |
| `FLOWSEAL_UPSTREAM` | Только для тестов: путь к локальному клону Flowseal |

## Настройки `/etc/zapret-flowseal/config.json`

```json
{
  "upstream_repo": "https://github.com/Flowseal/zapret-discord-youtube.git",
  "upstream_branch": "main",
  "engine_repo": "https://github.com/bol-van/zapret2.git",
  "engine_version": "v1.0.7",
  "engine_dir": "/opt/zapret2",
  "work_dir": "/opt/zapret2/flowseal",
  "config_dir": "/etc/zapret-flowseal",
  "strategy": "general (FAKE TLS AUTO)",
  "game_filter": "off",
  "game_filter_tcp": "1024-65535",
  "game_filter_udp": "1024-65535",
  "auto_restart": true,
  "auto_engine_update": false
}
```

`auto_engine_update: false` означает: движок обновляется только явным `zapret update --engine`.
