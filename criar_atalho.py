import os
import subprocess

desktop = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), 'Desktop')
target_folder = os.path.dirname(os.path.abspath(__file__))
vbs_path = os.path.join(target_folder, 'Iniciar_App_Silencioso.vbs')
icon_path = os.path.join(target_folder, 'icon.ico')
lnk_path = os.path.join(desktop, 'InstaReels Studio.lnk')

ps_commands = [
    '$WshShell = New-Object -ComObject WScript.Shell',
    f'$Shortcut = $WshShell.CreateShortcut("{lnk_path}")',
    '$Shortcut.TargetPath = "wscript.exe"',
    f'$Shortcut.Arguments = \'"{vbs_path}"\'',
    f'$Shortcut.WorkingDirectory = "{target_folder}"',
    f'$Shortcut.IconLocation = "{icon_path}"',
    '$Shortcut.Save()'
]

ps_code = "; ".join(ps_commands)
res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_code], capture_output=True, text=True)
if res.returncode == 0:
    print(f"Atalho criado na Área de Trabalho: {lnk_path}")
else:
    print(f"Erro: {res.stderr}")
