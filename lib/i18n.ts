import type { Language } from "./types";

export const translations: Record<string, Record<Language, string>> = {
  // Navigation
  "nav.connect": { pl: "Połącz", en: "Connect", de: "Verbinden", fr: "Connecter", zh: "连接" },
  "nav.calibration": { pl: "Kalibracja", en: "Calibration", de: "Kalibrierung", fr: "Calibrage", zh: "校准" },
  "nav.drills": { pl: "Drille", en: "Drills", de: "Drills", fr: "Lancers", zh: "训练方案" },
  "nav.training": { pl: "Trening", en: "Training", de: "Training", fr: "Entraînement", zh: "训练计划" },
  "nav.exercises": { pl: "Ćwiczenia", en: "Exercises", de: "Übungen", fr: "Exercices", zh: "体能训练" },
  "nav.camera": { pl: "Kamera", en: "Camera", de: "Kamera", fr: "Caméra", zh: "摄像头" },
  "nav.logs": { pl: "Logi", en: "Logs", de: "Protokolle", fr: "Journaux", zh: "日志" },

  // Connection status
  "status.connected": { pl: "Połączono", en: "Connected", de: "Verbunden", fr: "Connecté", zh: "已连接" },
  "status.offline": { pl: "Offline", en: "Offline", de: "Offline", fr: "Hors ligne", zh: "离线" },
  "status.simulation": { pl: "Symulacja", en: "Simulation", de: "Simulation", fr: "Simulation", zh: "模拟" },

  // Roles
  "role.controller": { pl: "Kontroler", en: "Controller", de: "Controller", fr: "Contrôleur", zh: "控制器" },
  "role.observer": { pl: "Obserwator", en: "Observer", de: "Beobachter", fr: "Observateur", zh: "观察者" },
  "role.pending": { pl: "Oczekuje", en: "Pending", de: "Wartend", fr: "En attente", zh: "等待中" },

  // Connect tab
  "connect.ble.title": { pl: "Bluetooth (BLE)", en: "Bluetooth (BLE)", de: "Bluetooth (BLE)", fr: "Bluetooth (BLE)", zh: "蓝牙 (BLE)" },
  "connect.ble.scan": { pl: "Skanuj urządzenia BLE", en: "Scan BLE Devices", de: "BLE-Geräte scannen", fr: "Scanner appareils BLE", zh: "扫描BLE设备" },
  "connect.usb.title": { pl: "USB (kabel)", en: "USB (cable)", de: "USB (Kabel)", fr: "USB (câble)", zh: "USB（线缆）" },
  "connect.usb.scan": { pl: "Szukaj portów USB", en: "Scan USB Ports", de: "USB-Ports scannen", fr: "Scanner ports USB", zh: "扫描USB端口" },
  "connect.reconnect": { pl: "Połącz ponownie", en: "Reconnect Last Device", de: "Letztes Gerät verbinden", fr: "Reconnecter dernier", zh: "重连上次设备" },
  "connect.simulation": { pl: "Tryb symulacji", en: "Simulation Mode", de: "Simulationsmodus", fr: "Mode simulation", zh: "模拟模式" },
  "connect.disconnect": { pl: "Rozłącz", en: "Disconnect", de: "Trennen", fr: "Déconnecter", zh: "断开" },
  "connect.reset_ble": { pl: "Reset BLE", en: "Reset BLE", de: "BLE zurücksetzen", fr: "Réinitialiser BLE", zh: "重置BLE" },
  "connect.firmware": { pl: "Firmware", en: "Firmware", de: "Firmware", fr: "Firmware", zh: "固件" },
  "connect.calibrated": { pl: "Skalibrowano", en: "Calibrated", de: "Kalibriert", fr: "Calibré", zh: "已校准" },
  "connect.not_calibrated": { pl: "Nie skalibrowano", en: "Not calibrated", de: "Nicht kalibriert", fr: "Non calibré", zh: "未校准" },

  // Calibration
  "cal.head_position": { pl: "Pozycja głowicy", en: "Head position", de: "Kopfposition", fr: "Position de la tête", zh: "头部位置" },
  "cal.oscillation": { pl: "Oscylacja (lewo-prawo)", en: "Oscillation (left-right)", de: "Oszillation (links-rechts)", fr: "Oscillation (gauche-droite)", zh: "摆动（左右）" },
  "cal.height": { pl: "Wysokość (góra-dół)", en: "Height (up-down)", de: "Höhe (auf-ab)", fr: "Hauteur (haut-bas)", zh: "高度（上下）" },
  "cal.rotation": { pl: "Rotacja (pochylenie)", en: "Rotation (tilt)", de: "Rotation (Neigung)", fr: "Rotation (inclinaison)", zh: "旋转（倾斜）" },
  "cal.motors": { pl: "Silniki", en: "Motors", de: "Motoren", fr: "Moteurs", zh: "电机" },
  "cal.top_motor": { pl: "Silnik górny", en: "Top motor", de: "Oberer Motor", fr: "Moteur haut", zh: "上电机" },
  "cal.bottom_motor": { pl: "Silnik dolny", en: "Bottom motor", de: "Unterer Motor", fr: "Moteur bas", zh: "下电机" },
  "cal.wait_time": { pl: "Czas oczekiwania", en: "Wait time", de: "Wartezeit", fr: "Temps d'attente", zh: "等待时间" },
  "cal.send": { pl: "Wyślij", en: "Send", de: "Senden", fr: "Envoyer", zh: "发送" },
  "cal.throw": { pl: "Rzut", en: "Throw", de: "Wurf", fr: "Lancer", zh: "发射" },
  "cal.stop": { pl: "Stop", en: "Stop", de: "Stopp", fr: "Arrêt", zh: "停止" },
  "cal.reset": { pl: "Reset", en: "Reset", de: "Zurücksetzen", fr: "Réinitialiser", zh: "重置" },
  "cal.presets": { pl: "Presety", en: "Presets", de: "Voreinstellungen", fr: "Préréglages", zh: "预设" },
  "cal.load": { pl: "Wczytaj", en: "Load", de: "Laden", fr: "Charger", zh: "加载" },
  "cal.save_new": { pl: "Zapisz jako nowy", en: "Save as New", de: "Als neu speichern", fr: "Enregistrer nouveau", zh: "另存为" },
  "cal.overwrite": { pl: "Nadpisz", en: "Overwrite", de: "Überschreiben", fr: "Écraser", zh: "覆盖" },
  "cal.set_default": { pl: "Ustaw domyślny", en: "Set Default", de: "Als Standard", fr: "Définir par défaut", zh: "设为默认" },
  "cal.delete": { pl: "Usuń", en: "Delete", de: "Löschen", fr: "Supprimer", zh: "删除" },
  "cal.import": { pl: "Importuj JSON", en: "Import JSON", de: "JSON importieren", fr: "Importer JSON", zh: "导入JSON" },
  "cal.export": { pl: "Eksportuj JSON", en: "Export JSON", de: "JSON exportieren", fr: "Exporter JSON", zh: "导出JSON" },
  "cal.unsaved": { pl: "Niezapisane zmiany", en: "Unsaved changes", de: "Ungespeicherte Änderungen", fr: "Modifications non enregistrées", zh: "未保存的更改" },

  // Drills
  "drills.new_folder": { pl: "+ Nowy folder", en: "+ New Folder", de: "+ Neuer Ordner", fr: "+ Nouveau dossier", zh: "+ 新建文件夹" },
  "drills.run": { pl: "Uruchom", en: "Run", de: "Starten", fr: "Lancer", zh: "运行" },
  "drills.edit": { pl: "Edytuj", en: "Edit", de: "Bearbeiten", fr: "Modifier", zh: "编辑" },
  "drills.move": { pl: "Przenieś", en: "Move", de: "Verschieben", fr: "Déplacer", zh: "移动" },
  "drills.delete": { pl: "Usuń", en: "Delete", de: "Löschen", fr: "Supprimer", zh: "删除" },
  "drills.reset": { pl: "Przywróć", en: "Reset", de: "Zurücksetzen", fr: "Réinitialiser", zh: "重置" },
  "drills.factory": { pl: "Fabryczny", en: "Factory", de: "Werkseinstellung", fr: "Usine", zh: "出厂" },
  "drills.balls": { pl: "piłek", en: "balls", de: "Bälle", fr: "balles", zh: "球" },
  "drills.active": { pl: "Aktywny drill", en: "Active drill", de: "Aktiver Drill", fr: "Lancer actif", zh: "活动训练" },
  "drills.ball_of": { pl: "Piłka", en: "Ball", de: "Ball", fr: "Balle", zh: "球" },
  "drills.pause": { pl: "Pauza", en: "Pause", de: "Pause", fr: "Pause", zh: "暂停" },
  "drills.resume": { pl: "Wznów", en: "Resume", de: "Fortsetzen", fr: "Reprendre", zh: "继续" },
  "drills.stop": { pl: "Stop", en: "Stop", de: "Stopp", fr: "Arrêt", zh: "停止" },

  // Training
  "training.new": { pl: "+ Nowy trening", en: "+ New Training", de: "+ Neues Training", fr: "+ Nouvel entraînement", zh: "+ 新建训练" },
  "training.steps": { pl: "kroków", en: "steps", de: "Schritte", fr: "étapes", zh: "步骤" },
  "training.estimated": { pl: "szacowany czas", en: "estimated time", de: "geschätzte Zeit", fr: "temps estimé", zh: "预计时间" },
  "training.countdown": { pl: "Odliczanie", en: "Countdown", de: "Countdown", fr: "Décompte", zh: "倒计时" },
  "training.drill": { pl: "Drill", en: "Drill", de: "Drill", fr: "Lancer", zh: "训练" },
  "training.ball_count": { pl: "Liczba piłek", en: "Ball count", de: "Ballanzahl", fr: "Nombre de balles", zh: "球数" },
  "training.speed": { pl: "Prędkość", en: "Speed", de: "Geschwindigkeit", fr: "Vitesse", zh: "速度" },
  "training.pause_after": { pl: "Pauza po", en: "Pause after", de: "Pause nach", fr: "Pause après", zh: "之后暂停" },
  "training.step": { pl: "Krok", en: "Step", de: "Schritt", fr: "Étape", zh: "步骤" },
  "training.skip": { pl: "Pomiń krok", en: "Skip Step", de: "Schritt überspringen", fr: "Passer l'étape", zh: "跳过步骤" },
  "training.phase.countdown": { pl: "ODLICZANIE", en: "COUNTDOWN", de: "COUNTDOWN", fr: "DÉCOMPTE", zh: "倒计时" },
  "training.phase.drilling": { pl: "DRILL", en: "DRILLING", de: "DRILLING", fr: "LANCER", zh: "训练中" },
  "training.phase.pause": { pl: "PAUZA", en: "PAUSE", de: "PAUSE", fr: "PAUSE", zh: "暂停" },
  "training.phase.exercise": { pl: "ĆWICZENIE", en: "EXERCISE", de: "ÜBUNG", fr: "EXERCICE", zh: "练习" },
  "training.phase.done": { pl: "UKOŃCZONE", en: "DONE", de: "FERTIG", fr: "TERMINÉ", zh: "完成" },

  // Exercises
  "exercises.reset_durations": { pl: "Resetuj czasy", en: "Reset All Durations", de: "Alle Zeiten zurücksetzen", fr: "Réinitialiser toutes les durées", zh: "重置所有时长" },
  "exercises.run_solo": { pl: "Uruchom osobno", en: "Run Solo", de: "Solo starten", fr: "Lancer seul", zh: "单独运行" },

  // Camera
  "camera.unavailable": { pl: "Kamera niedostępna", en: "Camera unavailable", de: "Kamera nicht verfügbar", fr: "Caméra indisponible", zh: "摄像头不可用" },

  // Logs
  "logs.robot": { pl: "Log robota", en: "Robot Log", de: "Roboter-Log", fr: "Journal robot", zh: "机器人日志" },
  "logs.server": { pl: "Log serwera", en: "Server Log", de: "Server-Log", fr: "Journal serveur", zh: "服务器日志" },
  "logs.clear": { pl: "Wyczyść", en: "Clear", de: "Löschen", fr: "Effacer", zh: "清除" },
  "logs.copy_report": { pl: "Kopiuj raport diagnostyczny", en: "Copy Diagnostic Report", de: "Diagnosebericht kopieren", fr: "Copier rapport diagnostic", zh: "复制诊断报告" },

  // Sessions
  "sessions.title": { pl: "Sesje", en: "Sessions", de: "Sitzungen", fr: "Sessions", zh: "会话" },
  "sessions.release": { pl: "Oddaj kontrolę", en: "Release Control", de: "Steuerung freigeben", fr: "Libérer le contrôle", zh: "释放控制" },
  "sessions.takeover": { pl: "Przejmij kontrolę", en: "Request Takeover", de: "Übernahme anfordern", fr: "Demander le contrôle", zh: "请求接管" },
  "sessions.accept": { pl: "Akceptuj", en: "Accept", de: "Akzeptieren", fr: "Accepter", zh: "接受" },
  "sessions.decline": { pl: "Odrzuć", en: "Decline", de: "Ablehnen", fr: "Refuser", zh: "拒绝" },

  // Device info
  "device.info": { pl: "Informacje o urządzeniu", en: "Device Info", de: "Geräteinformationen", fr: "Infos appareil", zh: "设备信息" },
  "device.name": { pl: "Nazwa", en: "Name", de: "Name", fr: "Nom", zh: "名称" },
  "device.mac": { pl: "Adres MAC", en: "MAC Address", de: "MAC-Adresse", fr: "Adresse MAC", zh: "MAC地址" },
  "device.port": { pl: "Port", en: "Port", de: "Port", fr: "Port", zh: "端口" },
  "device.transport": { pl: "Transport", en: "Transport", de: "Transport", fr: "Transport", zh: "传输" },

  // Common
  "common.save": { pl: "Zapisz", en: "Save", de: "Speichern", fr: "Enregistrer", zh: "保存" },
  "common.cancel": { pl: "Anuluj", en: "Cancel", de: "Abbrechen", fr: "Annuler", zh: "取消" },
  "common.confirm": { pl: "Potwierdź", en: "Confirm", de: "Bestätigen", fr: "Confirmer", zh: "确认" },
  "common.close": { pl: "Zamknij", en: "Close", de: "Schließen", fr: "Fermer", zh: "关闭" },
  "common.name": { pl: "Nazwa", en: "Name", de: "Name", fr: "Nom", zh: "名称" },
  "common.description": { pl: "Opis", en: "Description", de: "Beschreibung", fr: "Description", zh: "描述" },
};

export function t(key: string, lang: Language): string {
  const entry = translations[key];
  if (!entry) return key;
  return entry[lang] || entry.en || key;
}
