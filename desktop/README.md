# YoroOS Desktop — приложения и Linux-редакция

YoroOS теперь гибрид **50/50**:

| Часть | Что это |
|---|---|
| **Linux 50%** | Дистрибутив на Debian 13 + KDE Plasma (красиво и плавно), Chromium, Wine для Windows-программ |
| **Своё 50%** | Собственное ядро *YoroOS Core* (второй режим загрузки ISO, см. корень репозитория) + собственный набор приложений ниже |

## Свои приложения (Python + Qt6)

| Команда | Приложение |
|---|---|
| `yoro-notepad` | 📝 Блокнот — редактор текста |
| `yoro-files` | 📁 Файлы — файловый менеджер (удаление — в настоящую корзину freedesktop) |
| `yoro-media` | 🎬 Медиа — аудио/видео плеер с плейлистом |
| `yoro-settings` | ⚙️ Центр Настроек — цвет акцента всех Yoro-приложений + переход в настройки KDE |
| `yoro-console` | 🖥 Консоль — команды bash + `yoro`, `yoro-apps`, `yoro-help` |
| `yoro-computer` | 💻 Мой компьютер — диски, папки, сведения о системе |
| `yoro-trash` | 🗑 Корзина — восстановить / удалить навсегда / очистить |
| `matronix-browser` | 🌐 Matronix Browser — свой браузер (движок Chromium/QtWebEngine) |
| `yoro-calculator` | 🧮 Калькулятор |
| `yoro-paint` | 🎨 Paint — рисование |

Запуск из исходников (нужен `python3-pyqt6` и `python3-pyqt6.qtmultimedia`):

```bash
./desktop/bin/yoro-notepad
# или установка в систему:
sudo ./desktop/install.sh
```

## Сборка полного ISO дистрибутива

На Debian/Ubuntu с сетью:

```bash
sudo apt install live-build xorriso squashfs-tools syslinux isolinux \
    grub-pc-bin grub-efi-amd64-bin shim-signed
sudo ./distro/build-iso.sh        # -> out/yoroos-desktop-amd64.iso
```

Или без локальной машины: GitHub Actions → workflow
**“Build YoroOS Desktop ISO (Linux)”** → Run workflow → ISO появится
в артефактах запуска.

Образ: Debian 13 (trixie), только оболочка KDE Plasma + SDDM (чужие
программы вырезаны — вместо них приложения Yoro выше), Wine (+wine32),
Yoro-приложения, русская локаль и раскладки RU/US, загрузка BIOS+UEFI
(подписанный Debian shim — работает на Hyper-V Gen2 с Secure Boot).

## Дорожная карта

- [ ] Добавить YoroOS Core (своё ядро) вторым пунктом GRUB в этот же ISO
      (нужен Multiboot-заголовок в ядре)
- [ ] Экран приветствия при первом входе, своя тема Plymouth/SDDM
- [ ] Магазин/лаунчер Windows-программ поверх Wine (как Bottles)
