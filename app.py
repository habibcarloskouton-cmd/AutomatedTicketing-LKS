import json
import os
import smtplib as smtp
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import cast

import pandas as pd

# Import dynamique de EmailConfig
try:
    from locars_config import EmailConfig
except ImportError:
    import sys
    import importlib.util

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        config_path = os.path.join(sys._MEIPASS, "config.py")
    elif getattr(sys, "frozen", False):
        config_path = os.path.join(os.path.dirname(sys.executable), "config.py")
    else:
        config_path = os.path.join(os.path.dirname(__file__), "config.py")

    if os.path.exists(config_path):
        spec = importlib.util.spec_from_file_location("config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        EmailConfig = config_module.EmailConfig
    else:
        raise ImportError(f"Cannot find EmailConfig; tried config import and config.py at {config_path}")

from constants import CONFIG_DIR, CONFIG_FILE, DOSSIER_TICKETS, LOG_DIR, SUPPORTED_IMAGE_FORMATS
from email_sender import EmailSender
from modern_ui import CardFrame, HoverButton, ModernUI
from ticket_generator import TicketGenerator
from utils import Utils

class TicketingApp:
    """Application principale de gestion des tickets"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Automated Ticketing System - Locars Edition")
        self.root.geometry("1200x900")
        self.root.minsize(1000, 700)

        self.email_config = EmailConfig()
        self.generator = TicketGenerator()
        self.sender: EmailSender | None = None
        self.df_participants = pd.DataFrame(columns=['Nom', 'Email', 'Type', 'Code'])
        self.template_choice = tk.StringVar(value="Standard (Bleu)")

        self._setup_styles()
        self._setup_ui()
        self._load_email_config()
        self._update_sender()

    def _setup_styles(self) -> None:
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Header.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Status.TLabel', font=('Arial', 9))

    def _update_sender(self) -> None:
        if self.email_config.is_valid:
            self.sender = EmailSender(self.email_config)

    def _save_email_config(self) -> None:
        self.email_config.sender = self.ent_sender_mail.get()
        self.email_config.password = self.ent_sender_pass.get()

        try:
            config_data = {
                "email": self.email_config.sender,
                "password": self.email_config.password
            }
            with open(CONFIG_FILE, "w", encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)
            self._log("📧 Configuration email sauvegardée")
            self._update_sender()
            messagebox.showinfo("Succès", "Identifiants enregistrés !")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de sauvegarder: {e}")

    def _load_email_config(self) -> None:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding='utf-8') as f:
                    config = json.load(f)
                    self.email_config.sender = config.get("email", "")
                    self.email_config.password = config.get("password", "")
                self._log("📂 Configuration email chargée")
                self.ent_sender_mail.insert(0, self.email_config.sender)
                self.ent_sender_pass.insert(0, self.email_config.password)
            except Exception as e:
                self._log(f"⚠️ Erreur chargement config: {e}")

    def _test_email_connection(self) -> None:
        self.email_config.sender = self.ent_sender_mail.get()
        self.email_config.password = self.ent_sender_pass.get()

        if not self.email_config.is_valid:
            messagebox.showwarning("Erreur", "Veuillez remplir l'email et le mot de passe.")
            return

        self._log("🔄 Test de connexion SMTP en cours...")

        def _test():
            try:
                import smtplib
                with smtplib.SMTP(self.email_config.smtp_server, self.email_config.smtp_port) as server:
                    server.starttls()
                    server.login(self.email_config.sender, self.email_config.password)
                self._log("✅ Connexion SMTP réussie !")
                self.root.after(0, lambda: messagebox.showinfo("Succès", "Connexion SMTP établie avec succès !"))
            except smtp.SMTPAuthenticationError:
                self._log("❌ Échec authentification SMTP")
                self.root.after(0, lambda: messagebox.showerror("Erreur", "Identifiants invalides."))
            except smtp.SMTPException as e:
                self._log(f"❌ Erreur SMTP: {str(e)}")
                self.root.after(0, lambda: messagebox.showerror("Erreur", f"Erreur SMTP: {str(e)}"))
            except Exception as e:
                self._log(f"❌ Erreur: {type(e).__name__}")
                self.root.after(0, lambda: messagebox.showerror("Erreur", f"Erreur: {str(e)}"))

        thread = threading.Thread(target=_test, daemon=True)
        thread.start()

    def _add_participant_manually(self) -> None:
        nom = self.ent_manual_name.get().strip()
        email = self.ent_manual_email.get().strip()
        p_type = self.combo_type.get()

        if not (nom and email):
            messagebox.showwarning("Champ requis", "Veuillez remplir le nom et l'email.")
            return

        new_row = {
            'Nom': nom,
            'Email': email,
            'Type': p_type,
            'Code': f"MAN-{int(time.time())}-{len(self.df_participants):03d}"
        }
        self.df_participants = pd.concat([self.df_participants, pd.DataFrame([new_row])], ignore_index=True)
        self._update_participant_count()
        self._log(f"👤 Ajouté: {nom} ({p_type})")
        self.ent_manual_name.delete(0, tk.END)
        self.ent_manual_email.delete(0, tk.END)

    def _update_participant_count(self) -> None:
        count = len(self.df_participants)
        self.lbl_count.config(text=f"{count} participant(s) chargé(s)")

    def _load_excel(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier Excel",
            filetypes=[("Excel", "*.xlsx *.xls"), ("Tous fichiers", "*.*")]
        )
        if not file_path:
            return

        try:
            df = cast(pd.DataFrame, pd.read_excel(file_path, sheet_name=0))
            required_cols = ['Nom', 'Email', 'Type']

            if not all(col in df.columns for col in required_cols):
                if messagebox.askyesno("Colonnes manquantes",
                                       f"Colonnes requises: {required_cols}\nVoulez-vous générer des données de test ?"):
                    self._generate_test_data()
                return

            if 'Code' not in df.columns:
                df['Code'] = [f"IMP-{i:04d}" for i in range(len(df))]

            self.df_participants = df
            self.lbl_file.config(text=os.path.basename(file_path), fg="green")
            self._update_participant_count()
            self._log(f"✅ {len(df)} participants chargés depuis {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Erreur de lecture", f"Impossible de lire le fichier:\n{e}")

    def _generate_test_data(self) -> None:
        data = {
            'Nom': ['Alice Martin', 'Bob Dupont', 'Charlie Bernard', 'Diana Petit', 'Eve Moreau'],
            'Email': ['alice@test.com', 'bob@test.com', 'charlie@test.com', 'diana@test.com', 'eve@test.com'],
            'Type': ['Standard', 'VIP', 'VVIP', 'Standard', 'VIP'],
            'Code': ['A001', 'B002', 'C003', 'D004', 'E005']
        }
        self.df_participants = pd.DataFrame(data)
        self.lbl_file.config(text="Données de test", fg="blue")
        self._update_participant_count()
        self._log("📊 Données de test générées (5 participants)")

    def _on_template_change(self, *args) -> None:
        is_custom = "Personnalisé" in self.template_choice.get()
        self.btn_custom_template.config(state=tk.NORMAL if is_custom else tk.DISABLED)

        if is_custom:
            self.lbl_template_info.config(text="", fg="black")
            self.lbl_qr_zone.config(text="", fg="black")
        else:
            self.generator.custom_template = None
            self.generator.qr_zone = None
            template_name = self.template_choice.get().split(" ")[0]
            self.lbl_template_info.config(text=f"Template {template_name.upper()}", fg="green")
            self.lbl_qr_zone.config(text="")

    def _load_custom_template(self) -> None:
        file_path = filedialog.askopenfilename(title="Sélectionner un template", filetypes=SUPPORTED_IMAGE_FORMATS)
        if not file_path:
            return

        success, message = self.generator.load_custom_template(file_path)

        if success:
            self.lbl_template_info.config(text=f"✓ {os.path.basename(file_path)}", fg="green")
            self.lbl_qr_zone.config(text=f"📍 {message}", fg="blue")
            self._log(f"✅ Template personnalisé: {message}")
        else:
            self.lbl_template_info.config(text="✗ Échec", fg="red")
            self.lbl_qr_zone.config(text=message, fg="red")
            messagebox.showerror("Erreur template", message)

    def _log(self, message: str) -> None:
        Utils.write_log(message)

        def _append():
            timestamp = time.strftime('%H:%M:%S')
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)

        if threading.current_thread() is threading.main_thread():
            _append()
        else:
            self.root.after(0, _append)

    def _start_process(self) -> None:
        if self.df_participants.empty:
            messagebox.showwarning("Aucune donnée", "Veuillez charger des participants ou générer des données de test.")
            return

        if not self.email_config.is_valid:
            if not messagebox.askyesno("Configuration email",
                                       "Aucune configuration email détectée.\nVoulez-vous continuer (sauvegarde locale uniquement) ?"):
                return

        event_info = {
            "nom": self.entry_event_name.get().strip() or "Événement Sans Nom",
            "lieu": self.entry_venue.get().strip(),
            "date": self.entry_date.get().strip()
        }

        self.btn_start.config(state=tk.DISABLED, text="⏳ Traitement...")
        self.root.config(cursor="watch")

        thread = threading.Thread(target=self._process_tickets, args=(event_info,), daemon=True)
        thread.start()

    def _process_tickets(self, event_info: dict[str, str]) -> None:
        total = len(self.df_participants)
        success_count = 0
        base_folder = DOSSIER_TICKETS
        folder_name = os.path.join(base_folder, f"Tickets_{Utils.sanitize_folder_name(event_info['nom'])}")

        if not Utils.ensure_directory(base_folder) or not Utils.ensure_directory(folder_name):
            self._log("❌ Impossible de créer le dossier de sortie")
            self._process_complete(success_count, total, "")
            return

        self._log(f"📁 Dossier: {folder_name}")
        self._log(f"🚀 Traitement de {total} participant(s)...")

        for i, row in self.df_participants.iterrows():
            participant = row.to_dict()
            ticket_type = participant.get('Type', 'Standard')
            img_buffer, filename = self.generator.generate_ticket_image(participant, event_info, ticket_type)

            if not img_buffer or not filename:
                self._log(f"❌ [{i+1}/{total}] Échec génération: {participant.get('Nom')}")
                continue

            file_path = os.path.join(folder_name, filename)
            try:
                with open(file_path, "wb") as f:
                    f.write(img_buffer.getvalue())
                self._log(f"💾 [{i+1}/{total}] Sauvegardé: {filename}")
            except Exception as e:
                self._log(f"❌ [{i+1}/{total}] Erreur sauvegarde: {e}")
                continue

            if self.sender and self.email_config.is_valid:
                email_buffer = Utils.copy_buffer(img_buffer)
                status, msg = self.sender.send_ticket(
                    participant['Email'],
                    participant['Nom'],
                    email_buffer,
                    filename,
                    event_info['nom']
                )
                if status:
                    success_count += 1
                    self._log(f"✅ [{i+1}/{total}] Email envoyé à {participant['Nom']}")
                else:
                    self._log(f"⚠️ [{i+1}/{total}] Email échoué pour {participant['Nom']}: {msg}")

            time.sleep(0.5)

        self._process_complete(success_count, total, folder_name)

    def _process_complete(self, success: int, total: int, folder: str) -> None:
        def _finalize():
            self._log(f"🏁 Terminé: {success}/{total} emails envoyés")
            if folder:
                self._log(f"📦 Tous les tickets dans: {folder}/")
                messagebox.showinfo("Terminé",
                                    f"Processus terminé !\n\n✅ {success}/{total} emails envoyés\n📁 Tickets sauvegardés dans: {folder}/")
            self.btn_start.config(state=tk.NORMAL, text="🚀 LANCER LA GÉNÉRATION")
            self.root.config(cursor="")

        if threading.current_thread() is threading.main_thread():
            _finalize()
        else:
            self.root.after(0, _finalize)

    def _setup_ui(self) -> None:
        self.root.configure(bg=ModernUI.COLORS["bg_dark"])
        header = tk.Frame(self.root, bg=ModernUI.COLORS["bg_card"], height=80)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)
        lbl_title = tk.Label(header, text="🎫 LCS Ticketing System 2026",
                             font=ModernUI.FONTS["header"],
                             bg=ModernUI.COLORS["bg_card"],
                             fg=ModernUI.COLORS["text_white"])
        lbl_title.place(relx=0.5, rely=0.5, anchor="center")
        main_container = tk.Frame(self.root, bg=ModernUI.COLORS["bg_dark"])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        canvas = tk.Canvas(main_container, bg=ModernUI.COLORS["bg_dark"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=ModernUI.COLORS["bg_dark"])
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y", padx=(5, 0))
        canvas.pack(side="left", fill="both", expand=True)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self._setup_config_section()
        self._setup_participants_section()
        mid_frame = tk.Frame(self.scrollable_frame, bg=ModernUI.COLORS["bg_dark"])
        mid_frame.pack(fill=tk.X, pady=10)
        left_col = tk.Frame(mid_frame, bg=ModernUI.COLORS["bg_dark"])
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        right_col = tk.Frame(mid_frame, bg=ModernUI.COLORS["bg_dark"])
        right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self._setup_template_section(left_col)
        self._setup_event_section(right_col)
        self._setup_action_section()
        self._setup_log_section()

    def _setup_config_section(self) -> None:
        frame = CardFrame(self.scrollable_frame, title="⚙️ SMTP Configuration")
        frame.pack(fill=tk.X, pady=(0, 15))
        inner = tk.Frame(frame, bg=ModernUI.COLORS["bg_card"])
        inner.pack(fill=tk.X)
        inner.grid_columnconfigure(1, weight=1)
        entry_style = {
            "bg": ModernUI.COLORS["bg_input"],
            "fg": "white",
            "insertbackground": "white",
            "relief": tk.FLAT,
            "font": ModernUI.FONTS["body"]
        }
        tk.Label(inner, text="Sender Email:", bg=ModernUI.COLORS["bg_card"], fg=ModernUI.COLORS["text_gray"], font=ModernUI.FONTS["body"]).grid(row=0, column=0, sticky="w", pady=5)
        self.ent_sender_mail = tk.Entry(inner, width=30, **entry_style)
        self.ent_sender_mail.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        tk.Label(inner, text="App Password:", bg=ModernUI.COLORS["bg_card"], fg=ModernUI.COLORS["text_gray"], font=ModernUI.FONTS["body"]).grid(row=1, column=0, sticky="w", pady=5)
        self.ent_sender_pass = tk.Entry(inner, width=30, show="*", **entry_style)
        self.ent_sender_pass.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        warn_lbl = tk.Label(inner, text="⚠️ Utilise un 'App Password' Gmail, pas ton mot de passe principal.",
                           bg="#3e2723", fg="#ffccbc", font=("Arial", 8), padx=10, pady=5, anchor="w")
        warn_lbl.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        btn_row = tk.Frame(inner, bg=ModernUI.COLORS["bg_card"])
        btn_row.grid(row=3, column=0, columnspan=2, sticky="e", pady=10)
        HoverButton(btn_row, text="💾 Sauvegarder", command=self._save_email_config,
                   bg=ModernUI.COLORS["btn_secondary"], fg="white", relief=tk.FLAT, padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        HoverButton(btn_row, text="🔄 Tester Connexion", command=self._test_email_connection,
                   bg=ModernUI.COLORS["success"], fg="white", relief=tk.FLAT, padx=15, pady=5).pack(side=tk.LEFT, padx=5)

    def _setup_participants_section(self) -> None:
        frame = CardFrame(self.scrollable_frame, title="👥 Gestion des Participants")
        frame.pack(fill=tk.X, pady=15)
        top_bar = tk.Frame(frame, bg=ModernUI.COLORS["bg_card"])
        top_bar.pack(fill=tk.X, pady=(0, 15))
        self.lbl_count = tk.Label(top_bar, text="0 Participants",
                                 font=("Segoe UI", 14, "bold"),
                                 bg=ModernUI.COLORS["bg_card"], fg=ModernUI.COLORS["text_main"])
        self.lbl_count.pack(side=tk.LEFT)
        input_group = tk.Frame(frame, bg=ModernUI.COLORS["bg_card"])
        input_group.pack(fill=tk.X)
        entry_style = {"bg": ModernUI.COLORS["bg_input"], "fg": "white", "relief": tk.FLAT, "font": ModernUI.FONTS["body"]}
        tk.Label(input_group, text="Nom:", bg=ModernUI.COLORS["bg_card"], fg="white").pack(side=tk.LEFT, padx=(0,5))
        self.ent_manual_name = tk.Entry(input_group, width=15, **entry_style)
        self.ent_manual_name.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        tk.Label(input_group, text="Email:", bg=ModernUI.COLORS["bg_card"], fg="white").pack(side=tk.LEFT, padx=(10,5))
        self.ent_manual_email = tk.Entry(input_group, width=20, **entry_style)
        self.ent_manual_email.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.combo_type = ttk.Combobox(input_group, values=["Standard", "VIP", "VVIP"], width=8, state="readonly")
        self.combo_type.set("Standard")
        self.combo_type.pack(side=tk.LEFT, padx=10)
        HoverButton(input_group, text="+ Ajouter", command=self._add_participant_manually,
                   bg=ModernUI.COLORS["btn_primary"], fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=10)
        file_area = tk.Frame(frame, bg="#0f3460", pady=10)
        file_area.pack(fill=tk.X, pady=15)
        HoverButton(file_area, text="📁 Charger Excel", command=self._load_excel,
                   bg="#0f3460", fg=ModernUI.COLORS["text_white"], relief=tk.FLAT, font=("Arial", 10, "underline")).pack(side=tk.LEFT, padx=20)
        HoverButton(file_area, text="🧪 Générer Données Test", command=self._generate_test_data,
                   bg="#0f3460", fg=ModernUI.COLORS["text_gray"], relief=tk.FLAT, font=("Arial", 9)).pack(side=tk.LEFT)
        self.lbl_file = tk.Label(file_area, text="Aucun fichier sélectionné", bg="#0f3460", fg=ModernUI.COLORS["text_gray"])
        self.lbl_file.pack(side=tk.LEFT, padx=20)

    def _setup_template_section(self, parent) -> None:
        frame = CardFrame(parent, title="🎨 Design du Ticket")
        frame.pack(fill=tk.BOTH, expand=True, pady=15)
        cards_frame = tk.Frame(frame, bg=ModernUI.COLORS["bg_card"])
        cards_frame.pack(fill=tk.X, pady=10)
        select_frame = tk.Frame(cards_frame, bg=ModernUI.COLORS["bg_card"])
        select_frame.pack(fill=tk.X)
        tk.Label(select_frame, text="Sélectionner le style:", bg=ModernUI.COLORS["bg_card"], fg="white").pack(side=tk.LEFT)
        style = ttk.Style()
        style.configure("TCombobox", fieldbackground=ModernUI.COLORS["bg_input"], background=ModernUI.COLORS["bg_card"], foreground="white")
        template_combo = ttk.Combobox(select_frame, textvariable=self.template_choice,
                                      values=["Standard (Bleu)", "VIP (Or)", "VVIP (Noir)", "Personnalisé"],
                                      width=20, state="readonly")
        template_combo.set("Standard (Bleu)")
        template_combo.pack(side=tk.LEFT, padx=10)
        template_combo.bind("<<ComboboxSelected>>", self._on_template_change)
        self.btn_custom_template = HoverButton(select_frame, text="📂 Charger Template",
                                              command=self._load_custom_template,
                                              bg=ModernUI.COLORS["btn_secondary"],
                                              fg="white", relief=tk.FLAT, padx=10, state=tk.DISABLED)
        self.btn_custom_template.pack(side=tk.LEFT, padx=5)
        info_panel = tk.Frame(frame, bg="#000000", relief=tk.SUNKEN, borderwidth=1)
        info_panel.pack(fill=tk.X, pady=10, padx=5)
        self.lbl_template_info = tk.Label(info_panel, text="Template: Standard (Bleu)",
                                         bg="#000000", fg="#2ecc71", font=ModernUI.FONTS["mono"], anchor="w")
        self.lbl_template_info.pack(fill=tk.X, padx=10, pady=5)
        self.lbl_qr_zone = tk.Label(info_panel, text="Zone QR: à charger si personnalisé",
                                   bg="#000000", fg="#3498db", font=ModernUI.FONTS["mono"], anchor="w")
        self.lbl_qr_zone.pack(fill=tk.X, padx=10, pady=5)

    def _setup_event_section(self, parent) -> None:
        frame = CardFrame(parent, title="📅 Détails de l'Événement")
        frame.pack(fill=tk.BOTH, expand=True, pady=15)
        inner = tk.Frame(frame, bg=ModernUI.COLORS["bg_card"])
        inner.pack(fill=tk.BOTH, expand=True)
        entry_style = {"bg": ModernUI.COLORS["bg_input"], "fg": "white", "relief": tk.FLAT, "font": ModernUI.FONTS["body"]}
        label_style = {"bg": ModernUI.COLORS["bg_card"], "fg": ModernUI.COLORS["text_gray"], "font": ModernUI.FONTS["body"]}
        for i, (label_text, default_val, var_name) in enumerate([
            ("Nom de l'événement", "LCS Championship 2026", "entry_event_name"),
            ("Lieu", "Accor Arena, Paris", "entry_venue"),
            ("Date & Heure", "15 Octobre 2026 - 20:00", "entry_date")
        ]):
            tk.Label(inner, text=label_text, **label_style).grid(row=i, column=0, sticky="w", pady=8)
            entry = tk.Entry(inner, width=30, **entry_style)
            entry.grid(row=i, column=1, padx=10, pady=8, sticky="ew")
            entry.insert(0, default_val)
            setattr(self, var_name, entry)
        inner.grid_columnconfigure(1, weight=1)

    def _setup_action_section(self) -> None:
        frame = tk.Frame(self.scrollable_frame, bg=ModernUI.COLORS["bg_dark"])
        frame.pack(fill=tk.X, pady=30)
        self.btn_start = HoverButton(frame, text="🚀 LANCER LA GÉNÉRATION & ENVOI",
                                    font=("Segoe UI", 14, "bold"),
                                    bg=ModernUI.COLORS["btn_primary"],
                                    fg="white",
                                    relief=tk.FLAT,
                                    height=2,
                                    cursor="hand2")
        self.btn_start.config(command=self._start_process)
        self.btn_start.pack(fill=tk.X, padx=40)
        shadow = tk.Frame(frame, bg="#000000", height=5)
        shadow.pack(fill=tk.X, padx=50)

    def _setup_log_section(self) -> None:
        frame = CardFrame(self.scrollable_frame, title="📋 Journal Système")
        frame.pack(fill=tk.BOTH, expand=True, pady=15)
        self.log_text = tk.Text(frame, height=10, font=ModernUI.FONTS["mono"],
                               bg="#000000", fg="#00ff00",
                               insertbackground="#00ff00",
                               relief=tk.FLAT, padx=10, pady=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scroll = ttk.Scrollbar(frame, command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scroll.set)


def main():
    Utils.ensure_directory(CONFIG_DIR)
    Utils.ensure_directory(LOG_DIR)
    Utils.ensure_directory(DOSSIER_TICKETS)

    root = tk.Tk()
    root.minsize(800, 600)
    try:
        root.iconbitmap("icon.ico")
    except Exception:
        pass

    app = TicketingApp(root)

    def on_closing():
        if messagebox.askokcancel("Quitter", "Arrêter le processus en cours ?"):
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
