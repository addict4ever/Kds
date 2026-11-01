import os
import json
import csv
import math
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

LOG_DIR = r"C:\resto_controller\temperature"


class CalendarWidget(tk.Frame):
    """Calendrier interactif pur Python surlignant les dates contenant des données."""
    def __init__(self, parent, available_dates, on_date_change, dark_mode=False):
        super().__init__(parent)
        self.available_dates = available_dates
        self.on_date_change = on_date_change
        self.dark_mode = dark_mode
        
        self.current_date = datetime.now()
        self.year = self.current_date.year
        self.month = self.current_date.month
        self.selected_start = None
        self.selected_end = None
        
        self.apply_theme()

    def apply_theme(self):
        bg = "#222222" if self.dark_mode else "white"
        fg = "#ffffff" if self.dark_mode else "black"
        header_bg = "#333333" if self.dark_mode else "#2c3e50"
        days_bg = "#2a2a2a" if self.dark_mode else "#ecf0f1"
        days_fg = "#aaaaaa" if self.dark_mode else "#7f8c8d"
        
        self.configure(bg=bg)
        
        if hasattr(self, 'header'): self.header.destroy()
        if hasattr(self, 'days_frame'): self.days_frame.destroy()
        if hasattr(self, 'grid_frame'): self.grid_frame.destroy()

        self.header = tk.Frame(self, bg=header_bg)
        self.header.pack(fill=tk.X)
        
        btn_prev = tk.Button(self.header, text="◄", command=self.prev_month, bg=header_bg, fg=fg, bd=0, font=("Segoe UI", 9, "bold"))
        btn_prev.pack(side=tk.LEFT, padx=5, pady=3)
        
        self.lbl_month = tk.Label(self.header, text="", font=("Segoe UI", 10, "bold"), bg=header_bg, fg=fg)
        self.lbl_month.pack(side=tk.LEFT, expand=True)
        
        btn_next = tk.Button(self.header, text="►", command=self.next_month, bg=header_bg, fg=fg, bd=0, font=("Segoe UI", 9, "bold"))
        btn_next.pack(side=tk.RIGHT, padx=5, pady=3)
        
        self.days_frame = tk.Frame(self, bg=days_bg)
        self.days_frame.pack(fill=tk.X)
        for d in ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]:
            lbl = tk.Label(self.days_frame, text=d, font=("Segoe UI", 8, "bold"), bg=days_bg, fg=days_fg, width=4)
            lbl.pack(side=tk.LEFT, expand=True)

        self.grid_frame = tk.Frame(self, bg=bg)
        self.grid_frame.pack(fill=tk.BOTH, expand=True)
        
        self.render_calendar()

    def prev_month(self):
        first = datetime(self.year, self.month, 1) - timedelta(days=1)
        self.year = first.year
        self.month = first.month
        self.render_calendar()

    def next_month(self):
        if self.month == 12:
            self.year += 1
            self.month = 1
        else:
            self.month += 1
        self.render_calendar()

    def render_calendar(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()
            
        self.lbl_month.config(text=f"{datetime(self.year, self.month, 1).strftime('%B %Y').capitalize()}")
        
        first_day = datetime(self.year, self.month, 1)
        start_weekday = first_day.weekday()
        
        if self.month == 12:
            next_m = datetime(self.year + 1, 1, 1)
        else:
            next_m = datetime(self.year, self.month + 1, 1)
        num_days = (next_m - first_day).days
        
        row = 0
        col = start_weekday
        
        bg_default = "#333333" if self.dark_mode else "white"
        fg_default = "#ffffff" if self.dark_mode else "black"

        for day in range(1, num_days + 1):
            date_str = f"{self.year:04d}-{self.month:02d}-{day:02d}"
            has_data = date_str in self.available_dates
            
            is_selected = False
            if self.selected_start and not self.selected_end:
                is_selected = (date_str == self.selected_start)
            elif self.selected_start and self.selected_end:
                is_selected = (self.selected_start <= date_str <= self.selected_end)
                
            bg_col = bg_default
            fg_col = fg_default
            font_style = ("Segoe UI", 9)
            
            if is_selected:
                bg_col = "#2980b9"
                fg_col = "white"
                font_style = ("Segoe UI", 9, "bold")
            elif has_data:
                bg_col = "#27ae60"
                fg_col = "white"
                font_style = ("Segoe UI", 9, "bold")
                
            btn = tk.Button(
                self.grid_frame, text=str(day), bg=bg_col, fg=fg_col, font=font_style, relief="flat", bd=1,
                command=lambda d=date_str: self.on_day_click(d)
            )
            btn.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
            
            col += 1
            if col > 6:
                col = 0
                row += 1

        for i in range(7):
            self.grid_frame.columnconfigure(i, weight=1)

    def on_day_click(self, date_str):
        if not self.selected_start or (self.selected_start and self.selected_end):
            self.selected_start = date_str
            self.selected_end = None
        else:
            if date_str < self.selected_start:
                self.selected_end = self.selected_start
                self.selected_start = date_str
            else:
                self.selected_end = date_str
                
        self.render_calendar()
        self.on_date_change(self.selected_start, self.selected_end)


class AdvancedThermometerDashboard(tk.Toplevel):
    """Gestionnaire professionnel et tableau de bord complet de visualisation des thermomètres."""
    def __init__(self, parent, target_sensor=None):
        super().__init__(parent)
        self.title("Gestionnaire Professionnel - Analyse & Visualisation des Thermomètres")
        self.geometry("1350x850")
        self.target_sensor = target_sensor
        self.dark_mode = False
        
        self.available_dates = self.scan_available_dates()
        
        self.main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.left_frame = tk.Frame(self.main_paned, width=340)
        self.right_frame = tk.Frame(self.main_paned)
        
        self.main_paned.add(self.left_frame, weight=1)
        self.main_paned.add(self.right_frame, weight=4)

        self.init_left_panel()
        self.init_right_panel()
        self.apply_theme()

        if self.available_dates:
            latest = sorted(list(self.available_dates))[-1]
            self.current_start_date = latest
            self.calendar.selected_start = latest
            self.calendar.render_calendar()
            self.on_date_selected(latest, None)
        else:
            self.current_start_date = datetime.now().strftime("%Y-%m-%d")
            self.current_end_date = None
            self.load_and_refresh()

    def init_left_panel(self):
        top_ctrl = tk.Frame(self.left_frame, padx=5, pady=5)
        top_ctrl.pack(fill=tk.X)
        
        self.btn_theme = tk.Button(top_ctrl, text="🌙 Mode Sombre", command=self.toggle_theme, font=("Segoe UI", 9, "bold"), relief="raised")
        self.btn_theme.pack(fill=tk.X, pady=2)

        self.sensor_box = tk.LabelFrame(self.left_frame, text=" 🌡️ Capteur Actif ", font=("Segoe UI", 10, "bold"), padx=8, pady=8)
        self.sensor_box.pack(fill=tk.X, padx=5, pady=5)
        
        self.sensor_var = tk.StringVar(value=self.target_sensor if self.target_sensor else "Tous")
        self.combo_sensor = ttk.Combobox(self.sensor_box, textvariable=self.sensor_var, state="readonly")
        self.combo_sensor.pack(fill=tk.X, pady=5)
        self.combo_sensor.bind("<<ComboboxSelected>>", lambda e: self.load_and_refresh())

        self.time_box = tk.LabelFrame(self.left_frame, text=" ⏰ Filtre Horaire ", font=("Segoe UI", 10, "bold"), padx=8, pady=8)
        self.time_box.pack(fill=tk.X, padx=5, pady=5)
        
        f_time = tk.Frame(self.time_box)
        f_time.pack(fill=tk.X)
        tk.Label(f_time, text="De :", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.entry_t_start = tk.Entry(f_time, width=7, font=("Segoe UI", 9))
        self.entry_t_start.insert(0, "00:00")
        self.entry_t_start.pack(side=tk.LEFT, padx=3)
        
        tk.Label(f_time, text="À :", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(10, 0))
        self.entry_t_end = tk.Entry(f_time, width=7, font=("Segoe UI", 9))
        self.entry_t_end.insert(0, "23:59")
        self.entry_t_end.pack(side=tk.LEFT, padx=3)
        
        btn_apply_time = tk.Button(self.time_box, text="Appliquer Heure", command=self.load_and_refresh, font=("Segoe UI", 8, "bold"), padx=5, pady=2)
        btn_apply_time.pack(fill=tk.X, pady=(5, 0))

        self.cal_box = tk.LabelFrame(self.left_frame, text=" 📅 Calendrier des Données ", font=("Segoe UI", 10, "bold"), padx=8, pady=8)
        self.cal_box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.lbl_selected_range = tk.Label(self.cal_box, text="Sélectionnez une date", font=("Segoe UI", 9, "italic"))
        self.lbl_selected_range.pack(pady=2)
        
        self.calendar = CalendarWidget(self.cal_box, self.available_dates, self.on_date_selected, self.dark_mode)
        self.calendar.pack(fill=tk.BOTH, expand=True, pady=5)

        legend_frame = tk.Frame(self.cal_box)
        legend_frame.pack(fill=tk.X, pady=2)
        tk.Label(legend_frame, text="■ Données dispos", fg="#27ae60", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Label(legend_frame, text="■ Sélection", fg="#2980b9", font=("Segoe UI", 8, "bold")).pack(side=tk.RIGHT, padx=5)

    def init_right_panel(self):
        self.toolbar = tk.Frame(self.right_frame, padx=8, pady=8, relief="raised", bd=1)
        self.toolbar.pack(fill=tk.X, pady=(0, 5))

        tk.Label(self.toolbar, text="Vue graphique :", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=2)
        self.view_type_var = tk.StringVar(value="Courbe / Ligne")
        
        # 📊 MULTIPLES FORMATS DE VISUALISATION DISPONIBLES
        views = [
            "Courbe / Ligne", 
            "Barres Verticales (Histogramme)", 
            "Aire colorée sous la courbe", 
            "Nuage de points", 
            "Boîte à moustaches (Statistique)"
        ]
        self.combo_view = ttk.Combobox(self.toolbar, textvariable=self.view_type_var, values=views, state="readonly", width=30)
        self.combo_view.pack(side=tk.LEFT, padx=5)
        
        # 🔗 CHANGEMENT DYNAMIQUE INSTANTANÉ
        self.combo_view.bind("<<ComboboxSelected>>", lambda e: self.update_chart())

        self.ma_var = tk.BooleanVar(value=False)
        self.chk_ma = tk.Checkbutton(self.toolbar, text="Moyenne Mobile", variable=self.ma_var, command=self.update_chart, font=("Segoe UI", 9))
        self.chk_ma.pack(side=tk.LEFT, padx=5)

        tk.Label(self.toolbar, text="Seuil (°C):", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(5, 2))
        self.entry_threshold = tk.Entry(self.toolbar, width=5, font=("Segoe UI", 9))
        self.entry_threshold.insert(0, "5.0")
        self.entry_threshold.pack(side=tk.LEFT, padx=2)
        
        btn_threshold = tk.Button(self.toolbar, text="Tracer", command=self.update_chart, font=("Segoe UI", 8, "bold"), padx=4)
        btn_threshold.pack(side=tk.LEFT, padx=2)

        btn_export_png = tk.Button(self.toolbar, text="📷 PNG", command=self.export_png, font=("Segoe UI", 9, "bold"), bg="#2980b9", fg="white", padx=5)
        btn_export_png.pack(side=tk.RIGHT, padx=2)
        
        btn_export_json = tk.Button(self.toolbar, text="💾 JSON", command=self.export_json, font=("Segoe UI", 9, "bold"), bg="#8e44ad", fg="white", padx=5)
        btn_export_json.pack(side=tk.RIGHT, padx=2)

        btn_export_csv = tk.Button(self.toolbar, text="💾 CSV", command=self.export_csv, font=("Segoe UI", 9, "bold"), bg="#27ae60", fg="white", padx=5)
        btn_export_csv.pack(side=tk.RIGHT, padx=2)

        self.notebook = ttk.Notebook(self.right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Onglet 1 : Graphique Interactif
        self.tab_graph = tk.Frame(self.notebook)
        self.notebook.add(self.tab_graph, text="📊 Graphique Interactif")

        self.fig = Figure(figsize=(8, 4.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas_agg = FigureCanvasTkAgg(self.fig, master=self.tab_graph)
        self.canvas_agg.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Onglet 2 : Statistiques & Indicateurs
        self.tab_stats = tk.Frame(self.notebook, padx=15, pady=15)
        self.notebook.add(self.tab_stats, text="📈 Statistiques & Indicateurs")

        self.stats_tree = ttk.Treeview(self.tab_stats, columns=("sensor", "avg", "min", "max", "std", "alerts", "count"), show="headings")
        self.stats_tree.heading("sensor", text="Capteur")
        self.stats_tree.heading("avg", text="Moyenne (°C)")
        self.stats_tree.heading("min", text="Min (°C)")
        self.stats_tree.heading("max", text="Max (°C)")
        self.stats_tree.heading("std", text="Écart-type")
        self.stats_tree.heading("alerts", text="Alertes Seuil")
        self.stats_tree.heading("count", text="Total Relevés")
        
        for col in ("sensor", "avg", "min", "max", "std", "alerts", "count"):
            self.stats_tree.column(col, anchor="center", width=110)
        self.stats_tree.pack(fill=tk.BOTH, expand=True)

        # Onglet 3 : Données Brutes & Recherche
        self.tab_table = tk.Frame(self.notebook, padx=5, pady=5)
        self.notebook.add(self.tab_table, text="📋 Données Brutes & Recherche")

        search_bar = tk.Frame(self.tab_table, pady=5)
        search_bar.pack(fill=tk.X)
        tk.Label(search_bar, text="🔍 Filtrer les données :", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.filter_table())
        self.entry_search = tk.Entry(search_bar, textvariable=self.search_var, font=("Segoe UI", 9), width=30)
        self.entry_search.pack(side=tk.LEFT, padx=5)

        columns = ("date", "heure", "sensor", "valeur")
        self.tree = ttk.Treeview(self.tab_table, columns=columns, show="headings")
        self.tree.heading("date", text="Date")
        self.tree.heading("heure", text="Heure")
        self.tree.heading("sensor", text="Capteur")
        self.tree.heading("valeur", text="Température (°C)")
        
        for c in columns:
            self.tree.column(c, anchor="center", width=140)

        scrollbar = ttk.Scrollbar(self.tab_table, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.current_start_date = datetime.now().strftime("%Y-%m-%d")
        self.current_end_date = None
        self.loaded_data = []

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.btn_theme.config(text="☀️ Mode Clair" if self.dark_mode else "🌙 Mode Sombre")
        self.apply_theme()
        self.calendar.dark_mode = self.dark_mode
        self.calendar.apply_theme()
        self.update_chart()

    def apply_theme(self):
        bg = "#1e1e1e" if self.dark_mode else "#f4f7f6"
        card_bg = "#252526" if self.dark_mode else "white"
        
        self.configure(bg=bg)
        self.left_frame.config(bg=bg)
        self.right_frame.config(bg=bg)
        self.toolbar.config(bg=card_bg)
        
        if self.dark_mode:
            self.fig.patch.set_facecolor('#252526')
            self.ax.set_facecolor('#1e1e1e')
            self.ax.xaxis.label.set_color('white')
            self.ax.yaxis.label.set_color('white')
            self.ax.title.set_color('white')
            self.ax.tick_params(colors='white')
        else:
            self.fig.patch.set_facecolor('white')
            self.ax.set_facecolor('white')
            self.ax.xaxis.label.set_color('black')
            self.ax.yaxis.label.set_color('black')
            self.ax.title.set_color('black')
            self.ax.tick_params(colors='black')
        self.canvas_agg.draw()

    def scan_available_dates(self):
        dates = set()
        if os.path.exists(LOG_DIR):
            for fname in os.listdir(LOG_DIR):
                if fname.startswith("logs_") and fname.endswith(".json"):
                    d_str = fname.replace("logs_", "").replace(".json", "")
                    dates.add(d_str)
        return dates

    def on_date_selected(self, start_date, end_date):
        self.current_start_date = start_date
        self.current_end_date = end_date
        
        if end_date and end_date != start_date:
            self.lbl_selected_range.config(text=f"Plage : {start_date} au {end_date}", fg="#2980b9")
        else:
            self.lbl_selected_range.config(text=f"Date : {start_date}", fg="#27ae60")
            
        self.load_and_refresh()

    def load_and_refresh(self):
        self.loaded_data = []
        try:
            start = datetime.strptime(self.current_start_date, "%Y-%m-%d")
            end = datetime.strptime(self.current_end_date, "%Y-%m-%d") if self.current_end_date else start
        except Exception:
            return

        t_start_str = self.entry_t_start.get().strip() or "00:00"
        t_end_str = self.entry_t_end.get().strip() or "23:59"
        
        sensors_found = set()
        cur = start
        while cur <= end:
            d_str = cur.strftime("%Y-%m-%d")
            fpath = os.path.join(LOG_DIR, f"logs_{d_str}.json")
            if os.path.exists(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = json.load(f)
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict):
                                    s_name = item.get("sensor", "Inconnu")
                                    sensors_found.add(s_name)
                                    heure = item.get("heure", "00:00:00")
                                    if t_start_str <= heure[:5] <= t_end_str:
                                        selected_s = self.sensor_var.get()
                                        if selected_s == "Tous" or selected_s == s_name:
                                            self.loaded_data.append({
                                                "date": d_str,
                                                "heure": heure,
                                                "datetime": f"{d_str} {heure}",
                                                "sensor": s_name,
                                                "val": float(item.get("val", 0.0))
                                            })
                except Exception:
                    pass
            cur += timedelta(days=1)

        current_list = ["Tous"] + sorted(list(sensors_found))
        self.combo_sensor["values"] = current_list

        self.update_chart()
        self.update_stats()
        self.filter_table()

    def update_chart(self):
        # 🧹 Nettoyage complet de l'axe précédent pour éviter les superpositions
        self.ax.clear()
        view = self.view_type_var.get()
        use_ma = self.ma_var.get()

        if not self.loaded_data:
            self.ax.text(0.5, 0.5, "Aucune donnée disponible pour cette sélection", ha='center', va='center', transform=self.ax.transAxes, color="gray" if not self.dark_mode else "lightgray")
            self.canvas_agg.draw()
            return

        by_sensor = {}
        for d in self.loaded_data:
            s = d["sensor"]
            if s not in by_sensor: by_sensor[s] = []
            by_sensor[s].append(d)

        colors = ['#3498db', '#e67e22', '#2ecc71', '#9b59b6', '#f1c40f', '#e74c3c']

        # 📊 RENDU SELON LE TYPE DE VUE CHOISI
        if view == "Courbe / Ligne":
            for idx, (s_name, items) in enumerate(by_sensor.items()):
                x = [i["datetime"] for i in items]
                y = [i["val"] for i in items]
                c = colors[idx % len(colors)]
                self.ax.plot(x, y, marker="o", markersize=3, label=s_name, color=c, linewidth=1.5)
                if use_ma and len(y) >= 5:
                    ma_y = [sum(y[max(0, i-4):i+1])/len(y[max(0, i-4):i+1]) for i in range(len(y))]
                    self.ax.plot(x, ma_y, linestyle="--", label=f"{s_name} (Moy. Mobile)", color=c, alpha=0.7)
            self.ax.set_ylabel("Température (°C)")
            self.ax.legend(loc="upper left")
            self.ax.grid(True, linestyle="--", alpha=0.5)

        elif view == "Barres Verticales (Histogramme)":
            for idx, (s_name, items) in enumerate(by_sensor.items()):
                x = range(len(items))
                y = [i["val"] for i in items]
                labels_x = [i["datetime"] for i in items]
                c = colors[idx % len(colors)]
                self.ax.bar(x, y, label=s_name, color=c, alpha=0.8, width=0.7)
                self.ax.set_xticks(list(x))
                self.ax.set_xticklabels(labels_x, rotation=30, ha="right", fontsize=8)
            self.ax.set_ylabel("Température (°C)")
            self.ax.legend(loc="upper left")
            self.ax.grid(True, axis='y', linestyle="--", alpha=0.5)

        elif view == "Aire colorée sous la courbe":
            for idx, (s_name, items) in enumerate(by_sensor.items()):
                x = [i["datetime"] for i in items]
                y = [i["val"] for i in items]
                c = colors[idx % len(colors)]
                self.ax.plot(x, y, label=s_name, color=c)
                self.ax.fill_between(x, y, color=c, alpha=0.3)
            self.ax.set_ylabel("Température (°C)")
            self.ax.legend(loc="upper left")
            self.ax.grid(True, linestyle="--", alpha=0.5)

        elif view == "Nuage de points":
            for idx, (s_name, items) in enumerate(by_sensor.items()):
                x = [i["datetime"] for i in items]
                y = [i["val"] for i in items]
                c = colors[idx % len(colors)]
                self.ax.scatter(x, y, label=s_name, color=c, alpha=0.8, s=30)
            self.ax.set_ylabel("Température (°C)")
            self.ax.legend(loc="upper left")
            self.ax.grid(True, linestyle="--", alpha=0.5)

        elif view == "Boîte à moustaches (Statistique)":
            labels = []
            data_groups = []
            for s_name, items in by_sensor.items():
                labels.append(s_name)
                data_groups.append([i["val"] for i in items])
            self.ax.boxplot(data_groups, labels=labels, patch_artist=True)
            self.ax.set_ylabel("Température (°C)")
            self.ax.grid(True, axis='y', linestyle="--", alpha=0.5)

        # Tracé de la ligne de seuil d'alerte
        try:
            th_val = float(self.entry_threshold.get().strip())
            self.ax.axhline(y=th_val, color='red', linestyle='--', linewidth=1.5, label=f"Seuil Alerte ({th_val}°C)")
            self.ax.legend(loc="upper left")
        except ValueError:
            pass

        if view != "Boîte à moustaches (Statistique)" and view != "Barres Verticales (Histogramme)":
            total_pts = len(self.loaded_data)
            if total_pts > 10:
                step = total_pts // 8
                ticks = range(0, total_pts, step)
                labels = [self.loaded_data[i]["datetime"] for i in ticks]
                self.ax.set_xticks(ticks)
                self.ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=8)

        self.ax.set_title(f"Analyse Thermométrique - {view}", fontsize=11, fontweight="bold")
        self.fig.tight_layout()
        self.canvas_agg.draw() # 🔄 Redessin immédiat et forcé

    def update_stats(self):
        for row in self.stats_tree.get_children():
            self.stats_tree.delete(row)

        try:
            th_val = float(self.entry_threshold.get().strip())
        except ValueError:
            th_val = 999.0

        by_sensor = {}
        for d in self.loaded_data:
            s = d["sensor"]
            if s not in by_sensor: by_sensor[s] = []
            by_sensor[s].append(d["val"])

        for s_name, vals in by_sensor.items():
            if vals:
                n = len(vals)
                avg_val = sum(vals) / n
                min_val = min(vals)
                max_val = max(vals)
                variance = sum((v - avg_val) ** 2 for v in vals) / n
                std_val = math.sqrt(variance)
                alerts = sum(1 for v in vals if v > th_val)

                self.stats_tree.insert("", tk.END, values=(
                    s_name, 
                    f"{avg_val:.2f} °C", 
                    f"{min_val:.1f} °C", 
                    f"{max_val:.1f} °C", 
                    f"{std_val:.2f}",
                    f"{alerts} alerte(s)" if alerts > 0 else "0",
                    n
                ))

    def filter_table(self):
        query = self.search_var.get().lower().strip()
        for row in self.tree.get_children():
            self.tree.delete(row)

        try:
            th_val = float(self.entry_threshold.get().strip())
        except ValueError:
            th_val = 999.0

        for d in self.loaded_data:
            row_text = f"{d['date']} {d['heure']} {d['sensor']} {d['val']}".lower()
            if not query or query in row_text:
                tag = "alert" if d["val"] > th_val else "normal"
                self.tree.insert("", tk.END, values=(d["date"], d["heure"], d["sensor"], f"{d['val']:.1f} °C"), tags=(tag,))

        self.tree.tag_configure("alert", foreground="#c0392b", font=("Segoe UI", 9, "bold"))

    def export_csv(self):
        if not self.loaded_data:
            messagebox.showwarning("Export", "Aucune donnée à exporter.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            try:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(["Date", "Heure", "Capteur", "Temperature_C"])
                    for d in self.loaded_data:
                        w.writerow([d["date"], d["heure"], d["sensor"], d["val"]])
                messagebox.showinfo("Succès", "Export CSV réussi !")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

    def export_json(self):
        if not self.loaded_data:
            messagebox.showwarning("Export", "Aucune donnée à exporter.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.loaded_data, f, indent=4, ensure_ascii=False)
                messagebox.showinfo("Succès", "Export JSON réussi !")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

    def export_png(self):
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("Image PNG", "*.png")])
        if path:
            try:
                self.fig.savefig(path, dpi=300, bbox_inches='tight')
                messagebox.showinfo("Succès", "Graphique exporté en image PNG haute résolution !")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))