import itertools
import os
import dearpygui.dearpygui as dpg
from tts import tts
import kana
import romkan
import pykakasi

dpg.create_context()
dpg.create_viewport(title='Custom Title', width=800, height=600)
dpg.setup_dearpygui()



with dpg.font_registry():
    for file in os.listdir("fonts"):
        with dpg.font(os.path.join("fonts", file), 20, tag=os.path.splitext(file)[0]) as font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Japanese)
        
    dpg.bind_font("keifont")


with dpg.window(label="Kamishirasawa") as primary_window:
    dpg.add_text(default_value="上白沢　慧音")
    
    with dpg.menu_bar():
        with dpg.menu(label="Developement"):
            dpg.add_menu_item(label="Font manager", callback=dpg.show_font_manager)
            dpg.add_menu_item(label="Style editor", callback=dpg.show_style_editor)
    
    for syllable in kana.romaji_syllables():
        dpg.add_text(romkan.to_hiragana(syllable))
            
with dpg.window(label="Hiragana table"):    
    with dpg.table(header_row=False):
        for _ in vowels:
            dpg.add_table_column(width_fixed=True)
            
        vowels = ["a", "i", "u", "e", "o"]
        consonants = ["", "k", "s", "t", "n", "h", "m", "y", "r", "w"]
        excluded_syllables = {"yi", "ye", "wu"}
        
        def add_hiragana_text(romaji):
            dpg.add_button(
                width=100,
                height=50,
                label=f"{romaji*3}\n{romkan.to_hiragana(romaji)}",
                callback=lambda: tts(romkan.to_hiragana(romaji), "ja"),
            )
        
        for consonant in consonants:
            with dpg.table_row():
                for vowel in vowels:
                    syllable = consonant + vowel
                    if syllable not in excluded_syllables:
                        add_hiragana_text(syllable)
                    else:
                        dpg.add_table_cell()
            
        with dpg.table_row():
            add_hiragana_text("n")
    
dpg.set_primary_window(primary_window, True)
    
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()