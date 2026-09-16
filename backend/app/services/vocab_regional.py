"""Craft vocabulary in the regional languages PAVHAN accepts.

Detecting that a sentence is Tamil is worth nothing on its own — the listing
engine needs the colour, the material, the size and the days of work out of
that sentence. These tables are the minimum vocabulary to do that: the words
an artisan actually uses about their own craft, per language.

Kept deliberately narrow. Ten languages times the whole dictionary would be
unmaintainable and mostly unused; ten languages times "the forty words that
appear in a product description" is both small and sufficient.

Everything maps to the same canonical English values the Hindi and English
tables already produce, so the downstream engine needs no changes at all.
"""

from __future__ import annotations

# --------------------------------------------------------------------- colour
COLOURS: dict[str, dict[str, str]] = {
    "mr": {"लाल": "Red", "निळा": "Blue", "हिरवा": "Green", "पिवळा": "Yellow",
           "काळा": "Black", "पांढरा": "White", "सोनेरी": "Gold", "गुलाबी": "Pink",
           "तपकिरी": "Brown", "नारिंगी": "Orange", "जांभळा": "Purple"},
    "bn": {"লাল": "Red", "নীল": "Blue", "সবুজ": "Green", "হলুদ": "Yellow",
           "কালো": "Black", "সাদা": "White", "সোনালী": "Gold", "গোলাপি": "Pink",
           "বাদামী": "Brown", "কমলা": "Orange", "বেগুনি": "Purple"},
    "as": {"ৰঙা": "Red", "নীলা": "Blue", "সেউজীয়া": "Green", "হালধীয়া": "Yellow",
           "ক'লা": "Black", "বগা": "White", "সোণালী": "Gold"},
    "ta": {"சிவப்பு": "Red", "நீலம்": "Blue", "பச்சை": "Green", "மஞ்சள்": "Yellow",
           "கருப்பு": "Black", "வெள்ளை": "White", "தங்கம்": "Gold", "இளஞ்சிவப்பு": "Pink",
           "பழுப்பு": "Brown", "ஆரஞ்சு": "Orange"},
    "te": {"ఎరుపు": "Red", "నీలం": "Blue", "ఆకుపచ్చ": "Green", "పసుపు": "Yellow",
           "నలుపు": "Black", "తెలుపు": "White", "బంగారు": "Gold", "గులాబీ": "Pink",
           "గోధుమ": "Brown", "నారింజ": "Orange"},
    "kn": {"ಕೆಂಪು": "Red", "ನೀಲಿ": "Blue", "ಹಸಿರು": "Green", "ಹಳದಿ": "Yellow",
           "ಕಪ್ಪು": "Black", "ಬಿಳಿ": "White", "ಚಿನ್ನದ": "Gold", "ಗುಲಾಬಿ": "Pink",
           "ಕಂದು": "Brown", "ಕಿತ್ತಳೆ": "Orange"},
    "ml": {"ചുവപ്പ്": "Red", "നീല": "Blue", "പച്ച": "Green", "മഞ്ഞ": "Yellow",
           "കറുപ്പ്": "Black", "വെള്ള": "White", "സ്വർണ്ണ": "Gold", "പിങ്ക്": "Pink",
           "തവിട്ട്": "Brown", "ഓറഞ്ച്": "Orange"},
    "gu": {"લાલ": "Red", "વાદળી": "Blue", "લીલો": "Green", "પીળો": "Yellow",
           "કાળો": "Black", "સફેદ": "White", "સોનેરી": "Gold", "ગુલાબી": "Pink",
           "કથ્થઈ": "Brown", "નારંગી": "Orange"},
    "pa": {"ਲਾਲ": "Red", "ਨੀਲਾ": "Blue", "ਹਰਾ": "Green", "ਪੀਲਾ": "Yellow",
           "ਕਾਲਾ": "Black", "ਚਿੱਟਾ": "White", "ਸੁਨਹਿਰੀ": "Gold", "ਗੁਲਾਬੀ": "Pink",
           "ਭੂਰਾ": "Brown", "ਸੰਤਰੀ": "Orange"},
    "or": {"ଲାଲ": "Red", "ନୀଳ": "Blue", "ସବୁଜ": "Green", "ହଳଦିଆ": "Yellow",
           "କଳା": "Black", "ଧଳା": "White", "ସୁନେଲି": "Gold", "ଗୋଲାପୀ": "Pink",
           "ମାଟିଆ": "Brown"},
}

# ------------------------------------------------------------------- material
MATERIALS: dict[str, dict[str, str]] = {
    "mr": {"रेशीम": "Pure Silk", "सुती": "Cotton", "कापूस": "Cotton", "लोकर": "Wool",
           "माती": "Terracotta Clay", "लाकूड": "Wood", "बांबू": "Bamboo",
           "पितळ": "Brass", "चांदी": "Silver", "काच": "Glass", "कापड": "Cotton"},
    "bn": {"রেশম": "Pure Silk", "সিল্ক": "Pure Silk", "সুতি": "Cotton", "তুলা": "Cotton",
           "উল": "Wool", "মাটি": "Terracotta Clay", "কাঠ": "Wood", "বাঁশ": "Bamboo",
           "পিতল": "Brass", "রুপা": "Silver", "কাপড়": "Cotton", "পাট": "Jute"},
    "as": {"পাট": "Jute", "মাটি": "Terracotta Clay", "বাঁহ": "Bamboo", "কাঠ": "Wood",
           "ৰেচম": "Pure Silk", "কপাহ": "Cotton"},
    "ta": {"பட்டு": "Pure Silk", "பருத்தி": "Cotton", "கம்பளி": "Wool",
           "களிமண்": "Terracotta Clay", "மரம்": "Wood", "மூங்கில்": "Bamboo",
           "பித்தளை": "Brass", "வெள்ளி": "Silver", "துணி": "Cotton"},
    "te": {"పట్టు": "Pure Silk", "పత్తి": "Cotton", "ఉన్ని": "Wool",
           "మట్టి": "Terracotta Clay", "కలప": "Wood", "వెదురు": "Bamboo",
           "ఇత్తడి": "Brass", "వెండి": "Silver", "వస్త్రం": "Cotton"},
    "kn": {"ರೇಷ್ಮೆ": "Pure Silk", "ಹತ್ತಿ": "Cotton", "ಉಣ್ಣೆ": "Wool",
           "ಮಣ್ಣು": "Terracotta Clay", "ಮರ": "Wood", "ಬಿದಿರು": "Bamboo",
           "ಹಿತ್ತಾಳೆ": "Brass", "ಬೆಳ್ಳಿ": "Silver", "ಬಟ್ಟೆ": "Cotton"},
    "ml": {"പട്ട്": "Pure Silk", "പരുത്തി": "Cotton", "കമ്പിളി": "Wool",
           "കളിമണ്ണ്": "Terracotta Clay", "മരം": "Wood", "മുള": "Bamboo",
           "പിച്ചള": "Brass", "വെള്ളി": "Silver", "തുണി": "Cotton"},
    "gu": {"રેશમ": "Pure Silk", "સુતરાઉ": "Cotton", "કપાસ": "Cotton", "ઊન": "Wool",
           "માટી": "Terracotta Clay", "લાકડું": "Wood", "વાંસ": "Bamboo",
           "પિત્તળ": "Brass", "ચાંદી": "Silver", "કાપડ": "Cotton"},
    "pa": {"ਰੇਸ਼ਮ": "Pure Silk", "ਸੂਤੀ": "Cotton", "ਕਪਾਹ": "Cotton", "ਉੱਨ": "Wool",
           "ਮਿੱਟੀ": "Terracotta Clay", "ਲੱਕੜ": "Wood", "ਬਾਂਸ": "Bamboo",
           "ਪਿੱਤਲ": "Brass", "ਚਾਂਦੀ": "Silver", "ਕੱਪੜਾ": "Cotton"},
    "or": {"ରେଶମ": "Pure Silk", "ସୂତା": "Cotton", "ମାଟି": "Terracotta Clay",
           "କାଠ": "Wood", "ବାଉଁଶ": "Bamboo", "ପିତ୍ତଳ": "Brass", "ଲୁଗା": "Cotton"},
}

# ------------------------------------------------------------- product nouns
NOUNS: dict[str, dict[str, str]] = {
    "mr": {"साडी": "Saree", "ओढणी": "Dupatta", "शाल": "Shawl", "भांडे": "Pot",
           "मडके": "Pot", "दिवा": "Diya", "टोपली": "Basket", "बाहुली": "Toy",
           "चित्र": "Painting", "मूर्ती": "Idol", "पिशवी": "Bag"},
    "bn": {"শাড়ি": "Saree", "ওড়না": "Dupatta", "শাল": "Shawl", "হাঁড়ি": "Pot",
           "প্রদীপ": "Diya", "ঝুড়ি": "Basket", "পুতুল": "Toy", "ছবি": "Painting",
           "মূর্তি": "Idol", "ব্যাগ": "Bag", "কাঁথা": "Quilt"},
    "as": {"শাড়ী": "Saree", "গামোচা": "Stole", "পাচি": "Basket", "মূৰ্তি": "Idol"},
    "ta": {"புடவை": "Saree", "சேலை": "Saree", "சால்வை": "Shawl", "பானை": "Pot",
           "விளக்கு": "Diya", "கூடை": "Basket", "பொம்மை": "Toy", "ஓவியம்": "Painting",
           "சிலை": "Idol", "பை": "Bag"},
    "te": {"చీర": "Saree", "దుప్పటి": "Shawl", "కుండ": "Pot", "దీపం": "Diya",
           "బుట్ట": "Basket", "బొమ్మ": "Toy", "చిత్రం": "Painting", "విగ్రహం": "Idol",
           "సంచి": "Bag"},
    "kn": {"ಸೀರೆ": "Saree", "ಶಾಲು": "Shawl", "ಮಡಕೆ": "Pot", "ದೀಪ": "Diya",
           "ಬುಟ್ಟಿ": "Basket", "ಗೊಂಬೆ": "Toy", "ಚಿತ್ರ": "Painting", "ಮೂರ್ತಿ": "Idol",
           "ಚೀಲ": "Bag"},
    "ml": {"സാരി": "Saree", "ഷാൾ": "Shawl", "കലം": "Pot", "വിളക്ക്": "Diya",
           "കൊട്ട": "Basket", "പാവ": "Toy", "ചിത്രം": "Painting", "വിഗ്രഹം": "Idol",
           "സഞ്ചി": "Bag"},
    "gu": {"સાડી": "Saree", "ઓઢણી": "Dupatta", "શાલ": "Shawl", "માટલું": "Pot",
           "દીવો": "Diya", "ટોપલી": "Basket", "રમકડું": "Toy", "ચિત્ર": "Painting",
           "મૂર્તિ": "Idol", "થેલી": "Bag"},
    "pa": {"ਸਾੜੀ": "Saree", "ਦੁਪੱਟਾ": "Dupatta", "ਸ਼ਾਲ": "Shawl", "ਭਾਂਡਾ": "Pot",
           "ਦੀਵਾ": "Diya", "ਟੋਕਰੀ": "Basket", "ਖਿਡੌਣਾ": "Toy", "ਤਸਵੀਰ": "Painting",
           "ਮੂਰਤੀ": "Idol", "ਥੈਲਾ": "Bag", "ਫੁਲਕਾਰੀ": "Dupatta"},
    "or": {"ଶାଢ଼ୀ": "Saree", "ଚାଦର": "Shawl", "ହାଣ୍ଡି": "Pot", "ଦୀପ": "Diya",
           "ଟୋକେଇ": "Basket", "ପୁତୁଳା": "Toy", "ଚିତ୍ର": "Painting", "ମୂର୍ତ୍ତି": "Idol"},
}

# --------------------------------------------------------------- technique
TECHNIQUES: dict[str, dict[str, str]] = {
    "mr": {"हाताने": "Handmade", "विणलेले": "Handwoven", "रंगवलेले": "Hand-painted",
           "कोरलेले": "Hand-carved", "भरतकाम": "Hand Embroidery"},
    "bn": {"হাতে": "Handmade", "বোনা": "Handwoven", "আঁকা": "Hand-painted",
           "খোদাই": "Hand-carved", "সূচিকর্ম": "Hand Embroidery"},
    "as": {"হাতেৰে": "Handmade", "বোৱা": "Handwoven"},
    "ta": {"கையால்": "Handmade", "நெய்த": "Handwoven", "வரைந்த": "Hand-painted",
           "செதுக்கிய": "Hand-carved", "எம்பிராய்டரி": "Hand Embroidery"},
    "te": {"చేతితో": "Handmade", "నేసిన": "Handwoven", "చిత్రించిన": "Hand-painted",
           "చెక్కిన": "Hand-carved"},
    "kn": {"ಕೈಯಿಂದ": "Handmade", "ನೇಯ್ದ": "Handwoven", "ಚಿತ್ರಿಸಿದ": "Hand-painted",
           "ಕೆತ್ತಿದ": "Hand-carved"},
    "ml": {"കൈകൊണ്ട്": "Handmade", "നെയ്ത": "Handwoven", "വരച്ച": "Hand-painted",
           "കൊത്തിയ": "Hand-carved"},
    "gu": {"હાથથી": "Handmade", "વણેલું": "Handwoven", "ચિતરેલું": "Hand-painted",
           "કોતરેલું": "Hand-carved", "ભરતકામ": "Hand Embroidery"},
    "pa": {"ਹੱਥ ਨਾਲ": "Handmade", "ਬੁਣਿਆ": "Handwoven", "ਚਿਤਰਿਆ": "Hand-painted",
           "ਕਢਾਈ": "Hand Embroidery"},
    "or": {"ହାତରେ": "Handmade", "ବୁଣା": "Handwoven", "ଆଙ୍କା": "Hand-painted"},
}

# ------------------------------------------------------------------- numbers
NUMBERS: dict[str, dict[str, float]] = {
    "mr": {"एक": 1, "दोन": 2, "तीन": 3, "चार": 4, "पाच": 5, "सहा": 6, "सात": 7,
           "आठ": 8, "नऊ": 9, "दहा": 10, "बारा": 12, "पंधरा": 15, "वीस": 20, "शंभर": 100},
    "bn": {"এক": 1, "দুই": 2, "তিন": 3, "চার": 4, "পাঁচ": 5, "ছয়": 6, "সাত": 7,
           "আট": 8, "নয়": 9, "দশ": 10, "বারো": 12, "পনেরো": 15, "কুড়ি": 20, "একশো": 100},
    "as": {"এক": 1, "দুই": 2, "তিনি": 3, "চাৰি": 4, "পাঁচ": 5, "দহ": 10},
    "ta": {"ஒன்று": 1, "இரண்டு": 2, "மூன்று": 3, "நான்கு": 4, "ஐந்து": 5, "ஆறு": 6,
           "ஏழு": 7, "எட்டு": 8, "ஒன்பது": 9, "பத்து": 10, "நூறு": 100},
    "te": {"ఒకటి": 1, "రెండు": 2, "మూడు": 3, "నాలుగు": 4, "ఐదు": 5, "ఆరు": 6,
           "ఏడు": 7, "ఎనిమిది": 8, "తొమ్మిది": 9, "పది": 10, "వంద": 100},
    "kn": {"ಒಂದು": 1, "ಎರಡು": 2, "ಮೂರು": 3, "ನಾಲ್ಕು": 4, "ಐದು": 5, "ಆರು": 6,
           "ಏಳು": 7, "ಎಂಟು": 8, "ಒಂಬತ್ತು": 9, "ಹತ್ತು": 10, "ನೂರು": 100},
    "ml": {"ഒന്ന്": 1, "രണ്ട്": 2, "മൂന്ന്": 3, "നാല്": 4, "അഞ്ച്": 5, "ആറ്": 6,
           "ഏഴ്": 7, "എട്ട്": 8, "ഒമ്പത്": 9, "പത്ത്": 10, "നൂറ്": 100},
    "gu": {"એક": 1, "બે": 2, "ત્રણ": 3, "ચાર": 4, "પાંચ": 5, "છ": 6, "સાત": 7,
           "આઠ": 8, "નવ": 9, "દસ": 10, "બાર": 12, "પંદર": 15, "સો": 100},
    "pa": {"ਇੱਕ": 1, "ਦੋ": 2, "ਤਿੰਨ": 3, "ਚਾਰ": 4, "ਪੰਜ": 5, "ਛੇ": 6, "ਸੱਤ": 7,
           "ਅੱਠ": 8, "ਨੌਂ": 9, "ਦਸ": 10, "ਬਾਰਾਂ": 12, "ਸੌ": 100},
    "or": {"ଏକ": 1, "ଦୁଇ": 2, "ତିନି": 3, "ଚାରି": 4, "ପାଞ୍ଚ": 5, "ଛଅ": 6, "ସାତ": 7,
           "ଆଠ": 8, "ନଅ": 9, "ଦଶ": 10, "ଶହ": 100},
}

# --------------------------------------------------------------------- units
UNITS: dict[str, dict[str, str]] = {
    "mr": {"मीटर": "metre", "ग्रॅम": "gram", "किलो": "kg", "इंच": "inch", "फूट": "feet",
           "दिवस": "day", "तास": "hour"},
    "bn": {"মিটার": "metre", "গ্রাম": "gram", "কেজি": "kg", "ইঞ্চি": "inch",
           "ফুট": "feet", "দিন": "day", "ঘন্টা": "hour"},
    "as": {"মিটাৰ": "metre", "গ্ৰাম": "gram", "দিন": "day"},
    "ta": {"மீட்டர்": "metre", "கிராம்": "gram", "கிலோ": "kg", "அங்குலம்": "inch",
           "நாள்": "day", "மணி": "hour"},
    "te": {"మీటర్": "metre", "గ్రాము": "gram", "కిలో": "kg", "అంగుళం": "inch",
           "రోజు": "day", "గంట": "hour"},
    "kn": {"ಮೀಟರ್": "metre", "ಗ್ರಾಂ": "gram", "ಕಿಲೋ": "kg", "ಇಂಚು": "inch",
           "ದಿನ": "day", "ಗಂಟೆ": "hour"},
    "ml": {"മീറ്റർ": "metre", "ഗ്രാം": "gram", "കിലോ": "kg", "ഇഞ്ച്": "inch",
           "ദിവസം": "day", "മണിക്കൂർ": "hour"},
    "gu": {"મીટર": "metre", "ગ્રામ": "gram", "કિલો": "kg", "ઇંચ": "inch",
           "દિવસ": "day", "કલાક": "hour"},
    "pa": {"ਮੀਟਰ": "metre", "ਗ੍ਰਾਮ": "gram", "ਕਿਲੋ": "kg", "ਇੰਚ": "inch",
           "ਦਿਨ": "day", "ਘੰਟਾ": "hour"},
    "or": {"ମିଟର": "metre", "ଗ୍ରାମ": "gram", "କିଲୋ": "kg", "ଇଞ୍ଚ": "inch",
           "ଦିନ": "day", "ଘଣ୍ଟା": "hour"},
}


def merged(table: dict[str, dict], code: str) -> dict:
    """One language's table. Unknown codes return an empty mapping."""
    return table.get(code, {})


def all_values(table: dict[str, dict]) -> dict:
    """Every language's entries in one mapping, for script-agnostic matching.

    Indic scripts do not overlap, so a Tamil word can never collide with a
    Gujarati one and merging is safe.
    """
    out: dict = {}
    for per_language in table.values():
        out.update(per_language)
    return out
