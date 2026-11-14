// MatroOS Game: one full-width bottom taskbar, with centered launchers.
// This template is used only when Plasma creates a new default panel; it does
// not rewrite an existing user's panels at every login.
var panel = new Panel;
panel.location = "bottom";
panel.height = 54;
panel.lengthMode = "fill";
panel.floating = false;
panel.opacity = "opaque";
panel.addWidget("org.kde.plasma.panelspacer");
var menu = panel.addWidget("org.kde.plasma.kickoff");
menu.currentConfigGroup = ["General"];
menu.writeConfig("icon", "matroos-logo");
var tasks = panel.addWidget("org.kde.plasma.icontasks");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("launchers", [
    "applications:yoro-files.desktop",
    "applications:matronix-browser.desktop",
    "applications:steam.desktop",
    "applications:net.lutris.Lutris.desktop"
]);
panel.addWidget("org.kde.plasma.panelspacer");
panel.addWidget("org.kde.plasma.systemtray");
panel.addWidget("org.kde.plasma.digitalclock");
panel.addWidget("org.kde.plasma.showdesktop");
