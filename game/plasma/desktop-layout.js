// Keep the KDE first-run layout mechanism; never reset an existing desktop.
loadTemplate("org.kde.plasma.desktop.defaultPanel");
var screens = desktopsForActivity(currentActivity());
for (var i = 0; i < screens.length; ++i) {
    screens[i].wallpaperPlugin = "org.kde.image";
    screens[i].currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    screens[i].writeConfig("Image", "file:///usr/share/wallpapers/MatroOSGame/matroos-game.png");
}
