def romaji_syllables():
    import itertools
    
    vowels = ["a", "i", "u", "e", "o"]
    consonants = ["", "k", "s", "", "", "", "", "", "", ]
    excluded_syllables = {"yi", "ye", "wu"}
    
    return [syllable for c, v in itertools.product(consonants, vowels) if (syllable := c + v) not in excluded_syllables] + ["nn"]

