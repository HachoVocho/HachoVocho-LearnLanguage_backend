import fasttext
import re

# Load FastText language detection model
model = fasttext.load_model('lid.176.bin')

def detect_word_language(word):
    # Clean the word
    word = re.sub(r'[^\w]', '', word).lower()
    if not word:
        return "Unknown"

    # Predict language using FastText
    prediction = model.predict(word)
    lang_label = prediction[0][0].replace("__label__", "")  # Extract language code
    confidence = prediction[1][0]

    return lang_label, confidence  # Return language code and confidence

def detect_sentence_languages(sentence):
    words = sentence.split()  # Split sentence into words
    word_languages = {}
    for word in words:
        lang_code, confidence = detect_word_language(word)
        word_languages[word] = {"language": lang_code, "confidence": confidence}
    return word_languages

# Example sentence
sentence = "Guten tag"
language_map = detect_sentence_languages(sentence)
print(language_map)
