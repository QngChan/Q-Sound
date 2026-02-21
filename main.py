import customtkinter as ctk
from scraper import MyInstantsScraper
from audio_engine import AudioEngine
import threading
import random
import time
import json
import os

class SoundboardApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MyInstants Soundboard Premium & Mic Hub")
        self.geometry("1100x880")
        
        self.scraper = MyInstantsScraper()
        self.engine = AudioEngine()
        
        self.current_page = 1
        self.is_loading = False
        self.all_sounds = []
        self.is_search_mode = False
        
        self.currently_playing_url = None
        self.active_button = None
        
        self.colors = [
            "#FF3B30", "#FF9500", "#FFCC00", "#4CD964", 
            "#5AC8FA", "#007AFF", "#5856D6", "#FF2D55"
        ]
        
        self.favorites_file = "favorites.json"
        self.favorites = self.load_favorites()
        
        ctk.set_appearance_mode("dark")
        self.setup_ui()
        self.load_next_page()
        self.monitor_scroll()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color="#121212")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="✨ SOUNDBOARD Pro", 
                                     font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.pack(pady=(30, 20), padx=20)
        
        # Removed legacy global stop button to make room for cleaner sidebar
        
        # --- AUDIO OUTPUT ---
        ctk.CTkLabel(self.sidebar_frame, text="AUDIO OUTPUTS (WHERE SOUNDS GO)", 
                    font=ctk.CTkFont(size=10, weight="bold"), text_color="gray").pack(padx=20, anchor="w", pady=(10,0))
        
        self.label_physical = ctk.CTkLabel(self.sidebar_frame, text="🎧 To My Ear (Speaker)", font=ctk.CTkFont(size=11))
        self.label_physical.pack(padx=20, anchor="w")
        self.physical_device_var = ctk.StringVar(value="Select Device")
        self.physical_option = ctk.CTkOptionMenu(self.sidebar_frame, variable=self.physical_device_var, fg_color="#2A2A2A")
        self.physical_option.pack(pady=(0, 10), padx=20, fill="x")
        
        self.label_virtual = ctk.CTkLabel(self.sidebar_frame, text="🎙️ To Others (Virtual Cable)", font=ctk.CTkFont(size=11))
        self.label_virtual.pack(padx=20, anchor="w")
        self.virtual_device_var = ctk.StringVar(value="Select Device")
        self.virtual_option = ctk.CTkOptionMenu(self.sidebar_frame, variable=self.virtual_device_var, fg_color="#2A2A2A")
        self.virtual_option.pack(pady=(0, 15), padx=20, fill="x")
        
        # --- MICROPHONE PASSTHROUGH ---
        ctk.CTkLabel(self.sidebar_frame, text="MICROPHONE HUB", 
                    font=ctk.CTkFont(size=10, weight="bold"), text_color="cyan").pack(padx=20, anchor="w", pady=(10,0))
        
        self.label_mic = ctk.CTkLabel(self.sidebar_frame, text="🎤 My Real Microphone", font=ctk.CTkFont(size=11))
        self.label_mic.pack(padx=20, anchor="w")
        self.mic_device_var = ctk.StringVar(value="Select Microphone")
        self.mic_option = ctk.CTkOptionMenu(self.sidebar_frame, variable=self.mic_device_var, fg_color="#2A2A2A")
        self.mic_option.pack(pady=(0, 10), padx=20, fill="x")
        
        self.passthrough_var = ctk.BooleanVar(value=False)
        self.passthrough_toggle = ctk.CTkCheckBox(self.sidebar_frame, text="Route Mic to Virtual Cable", 
                                                variable=self.passthrough_var, command=self.toggle_mic_passthrough,
                                                font=ctk.CTkFont(size=12, weight="bold"))
        self.passthrough_toggle.pack(pady=5, padx=20, anchor="w")
        
        ctk.CTkLabel(self.sidebar_frame, text="Enable this to let others hear you!", 
                    font=ctk.CTkFont(size=9), text_color="gray").pack(padx=20, anchor="w")

        self.refresh_btn = ctk.CTkButton(self.sidebar_frame, text="🔄 Refresh All Devices", 
                                       fg_color="transparent", border_width=1, border_color="#333",
                                       command=self.refresh_devices)
        self.refresh_btn.pack(pady=(20, 10), padx=20, fill="x")

        # --- VOLUME CONTROL ---
        ctk.CTkLabel(self.sidebar_frame, text="GLOBAL VOLUME", 
                    font=ctk.CTkFont(size=10, weight="bold"), text_color="#5AC8FA").pack(padx=20, anchor="w", pady=(20,0))
        
        self.volume_slider = ctk.CTkSlider(self.sidebar_frame, from_=0, to=1, 
                                          command=self.change_volume,
                                          progress_color="#007AFF", button_color="#007AFF")
        self.volume_slider.set(self.engine.volume)
        self.volume_slider.pack(pady=(5, 0), padx=20, fill="x")
        
        self.vol_label = ctk.CTkLabel(self.sidebar_frame, text=f"{int(self.engine.volume*100)}%", font=ctk.CTkFont(size=10))
        self.vol_label.pack(padx=20, anchor="e")
        
        # Main Area
        self.main_frame = ctk.CTkFrame(self, fg_color="#0A0A0A", corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        
        # Order of packing for consistent layout:
        # 1. Top Bar
        # 2. Loading indicator
        # 3. Playback Panel (Bottom)
        # 4. Content (Header + Results Frame)
        
        self.top_bar = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.top_bar.pack(fill="x", padx=30, pady=(20, 10))
        
        self.loading_indicator = ctk.CTkProgressBar(self.main_frame, height=2, corner_radius=0, 
                                                   fg_color="#0A0A0A", progress_color="#007AFF", 
                                                   mode="indeterminate")
        self.loading_indicator.pack(fill="x", side="top", pady=0)
        self.loading_indicator.set(0)
        
        self.playback_panel = ctk.CTkFrame(self.main_frame, height=80, fg_color="#121212", corner_radius=15, border_width=1, border_color="#333")
        # Pack bottom initially hidden
        self.playback_panel.pack_forget() 

        self.playing_name_label = ctk.CTkLabel(self.playback_panel, text="No sound playing", font=ctk.CTkFont(size=14, weight="bold"))
        self.playing_name_label.pack(side="left", padx=30)
        
        self.panel_stop_btn = ctk.CTkButton(self.playback_panel, text="STOP", width=100, height=40, corner_radius=20,
                                          fg_color="#E02020", hover_color="#B01010",
                                          font=ctk.CTkFont(size=13, weight="bold"),
                                          command=self.global_stop)
        self.panel_stop_btn.pack(side="right", padx=30)

        # Content Area
        self.search_entry = ctk.CTkEntry(self.top_bar, placeholder_text="Discover sounds...", height=45, corner_radius=15)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 15))
        self.search_entry.bind("<Return>", lambda e: self.search_sounds())
        
        self.search_btn = ctk.CTkButton(self.top_bar, text="Search", width=120, height=45, corner_radius=15, command=self.search_sounds)
        self.search_btn.pack(side="right")
        
        self.header_label = ctk.CTkLabel(self.main_frame, text="Trending in Turkey", font=ctk.CTkFont(size=18, weight="bold"), text_color="#AAA")
        self.header_label.pack(padx=30, pady=(10, 5), anchor="w")

        self.results_frame = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent")
        self.results_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.grid_container = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        self.grid_container.pack(fill="both", expand=True)
        
        self.cols = 8
        for i in range(self.cols):
            self.grid_container.grid_columnconfigure(i, weight=1)

        self.refresh_devices()

    def refresh_devices(self):
        outs = self.engine.get_output_devices()
        ins = self.engine.get_input_devices()
        
        out_names = [f"[{d['id']}] {d['name']}" for d in outs]
        in_names = [f"[{d['id']}] {d['name']}" for d in ins]
        
        self.physical_option.configure(values=out_names)
        self.virtual_option.configure(values=out_names)
        self.mic_option.configure(values=in_names)
        
        for name in out_names:
            if any(k in name for k in ["Speaker", "Headphone", "Hoparlör", "Kulaklık"]):
                if self.physical_device_var.get() == "Select Device": self.physical_device_var.set(name)
            if any(k in name for k in ["CABLE", "VB-Audio"]):
                if self.virtual_device_var.get() == "Select Device": self.virtual_device_var.set(name)
        
        for name in in_names:
            if any(k in name for k in ["Mic", "Mikrofon", "Headset"]):
                if self.mic_device_var.get() == "Select Microphone": self.mic_device_var.set(name)

    def toggle_mic_passthrough(self):
        if self.passthrough_var.get():
            # Start passthrough
            try:
                mic_val = self.mic_device_var.get()
                virt_val = self.virtual_device_var.get()
                if "]" in mic_val and "]" in virt_val:
                    mid = int(mic_val.split(']')[0][1:])
                    vid = int(virt_val.split(']')[0][1:])
                    success = self.engine.start_passthrough(mid, vid)
                    if not success: self.passthrough_var.set(False)
                else:
                    self.passthrough_var.set(False)
            except: self.passthrough_var.set(False)
        else:
            self.engine.stop_passthrough()

    def monitor_scroll(self):
        if not self.is_search_mode:
            try:
                canvas = self.results_frame._parent_canvas
                y_view = canvas.yview()
                if y_view[1] > 0.85 and not self.is_loading:
                    self.load_next_page()
            except: pass
        self.after(500, self.monitor_scroll)

    def load_next_page(self):
        if self.is_loading: return
        self.is_loading = True
        self.loading_indicator.start()
        def do_load():
            try:
                sounds = self.scraper.get_tr_trending(page=self.current_page)
                if sounds:
                    self.after(0, lambda: self.append_sounds(sounds))
                    self.current_page += 1
            except Exception as e:
                print(f"Load error: {e}")
            finally:
                self.is_loading = False
                self.after(0, self.loading_indicator.stop)
        threading.Thread(target=do_load, daemon=True).start()

    def search_sounds(self):
        query = self.search_entry.get()
        if not query: 
            self.is_search_mode = False
            self.current_page = 1
            self.clear_grid()
            self.header_label.configure(text="Trending in Turkey")
            self.load_next_page()
            return
        self.is_search_mode = True
        self.header_label.configure(text=f"Results for '{query}'")
        self.clear_grid()
        self.loading_indicator.start()
        def do_search():
            try:
                sounds = self.scraper.search(query)
                self.after(0, lambda: self.append_sounds(sounds))
            except Exception as e:
                print(f"Search error: {e}")
            finally:
                self.after(0, self.loading_indicator.stop)
        threading.Thread(target=do_search, daemon=True).start()

    def clear_grid(self):
        for child in self.grid_container.winfo_children():
            child.destroy()
        self.all_sounds = []

    def append_sounds(self, sounds):
        start_idx = len(self.all_sounds)
        self.all_sounds.extend(sounds)
        for i, sound in enumerate(sounds):
            curr_row, curr_col = divmod(start_idx + i, self.cols)
            container = ctk.CTkFrame(self.grid_container, fg_color="transparent")
            container.grid(row=curr_row, column=curr_col, padx=10, pady=15, sticky="n")
            self.after(i * 5, lambda c=container, s=sound: self.create_sound_item(c, s))

    def change_volume(self, val):
        self.engine.volume = float(val)
        self.vol_label.configure(text=f"{int(float(val)*100)}%")

    def load_favorites(self):
        if os.path.exists(self.favorites_file):
            try:
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: return []
        return []

    def save_favorites(self):
        try:
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, indent=4)
        except Exception as e:
            print(f"Error saving favorites: {e}")

    def toggle_favorite(self, sound, star_btn):
        found = next((f for f in self.favorites if f['url'] == sound['url']), None)
        if found:
            self.favorites.remove(found)
            star_btn.configure(text="☆", text_color="gray")
        else:
            self.favorites.append(sound)
            star_btn.configure(text="★", text_color="#FFD700")
        self.save_favorites()

    def create_sound_item(self, container, sound):
        color = random.choice(self.colors)
        
        # Premium Wrapper for layering
        wrapper = ctk.CTkFrame(container, fg_color="transparent")
        wrapper.pack()

        is_fav = any(f['url'] == sound['url'] for f in self.favorites)
        star_btn = ctk.CTkButton(wrapper, text="★" if is_fav else "☆", 
                                width=25, height=25, corner_radius=12,
                                fg_color="transparent", text_color="#FFD700" if is_fav else "gray",
                                hover_color="#222",
                                font=ctk.CTkFont(size=16),
                                command=lambda s=sound: self.toggle_favorite(s, star_btn))
        star_btn.place(relx=0.85, rely=0.15, anchor="center")

        btn = ctk.CTkButton(wrapper, text="", width=75, height=75, corner_radius=38,
                           fg_color=color, hover_color=color, border_width=4, border_color="#1A1A1A",
                           command=lambda s=sound: self.play_sound_toggle(s))
        btn.pack()
        btn.sound_url = sound['url']
        
        # Subtle premium hover effect
        btn.bind("<Enter>", lambda e, b=btn: b.configure(border_color="gray"))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(border_color="#1A1A1A" if self.currently_playing_url != b.sound_url else "white"))

        lbl = ctk.CTkLabel(container, text=sound['name'], font=ctk.CTkFont(size=11, weight="bold"),
                          wraplength=85, text_color="#DDD", cursor="hand2")
        lbl.pack(pady=(8, 0))
        lbl.bind("<Button-1>", lambda e, s=sound: self.play_sound_toggle(s))
        lbl.bind("<Enter>", lambda e, l=lbl: l.configure(text_color="#FFF"))
        lbl.bind("<Leave>", lambda e, l=lbl: l.configure(text_color="#DDD"))

    def global_stop(self, reset_url=True):
        self.engine.stop_all()
        if reset_url: self.after(0, self.reset_playback_ui)

    def reset_playback_ui(self):
        if self.active_button:
            try: self.active_button.configure(border_color="#1A1A1A", border_width=4)
            except: pass
        self.currently_playing_url = None
        self.active_button = None
        self.playback_panel.pack_forget()

    def play_sound_toggle(self, sound):
        # Removing individual stop toggle as requested. Use bottom panel STOP button instead.
        self.global_stop(reset_url=False)
        device_ids = []
        try:
            p_val = self.physical_device_var.get()
            v_val = self.virtual_device_var.get()
            if "]" in p_val: device_ids.append(int(p_val.split(']')[0][1:]))
            if "]" in v_val: 
                vid = int(v_val.split(']')[0][1:])
                if vid not in device_ids: device_ids.append(vid)
            if not device_ids: return
            self.currently_playing_url = sound['url']
            for item in self.grid_container.winfo_children():
                for subitem in item.winfo_children():
                    if isinstance(subitem, ctk.CTkButton) and getattr(subitem, 'sound_url', None) == sound['url']:
                        self.active_button = subitem
                        self.active_button.configure(border_color="white", border_width=5)
                        break
            
            # Show playback panel
            self.playing_name_label.configure(text=f"Playing: {sound['name']}")
            self.playback_panel.pack(side="bottom", fill="x", padx=30, pady=20)
            
            threading.Thread(target=self.engine.play_from_url, args=(sound['url'], device_ids, self.on_sound_finished), daemon=True).start()
        except Exception as e:
            print(f"Error: {e}")
            self.reset_playback_ui()

    def on_sound_finished(self):
        self.after(0, self.reset_playback_ui)

if __name__ == "__main__":
    app = SoundboardApp()
    app.mainloop()
