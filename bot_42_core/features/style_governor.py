# bot_42_core/features/style_governor.py

def ground_tone(text: str) -> str:
    """
    Converts verbose / poetic / therapist-like replies into a grounded, clear,
    Christ-aligned tone (Style A).

    Rules:
    - Short, direct sentences.
    - No metaphors, no story language.
    - No syrupy apology / therapy clichés.
    - Calm, dignified, controlled.
    - Encouraging clarity and responsibility.
    """

    if not text:
        return text

    # 1) Kill obviously "flowery" / prophetic metaphors
    bad_phrases = [
        # Flowery / story-like
        "once",
        "there was",
        "like a",
        "as if",
        "the light",
        "the flame",
        "seed",
        "field",
        "story",
        "tale",
        "whisper",
        "poetic",
        "gentle flame",
        "heart",
        "soul",
        "source",
        "journey",

        # Expanded therapy clichés
        "it's okay to not be okay",
        "you are stronger than you think",
        "healing is not linear",
        "your feelings are valid",
        "it's all part of the journey",
        "honor your emotions",
        "be gentle with yourself",
        "trust the process",
        "you deserve happiness",
        "you deserve love",
        "just breathe",
        "give yourself grace",
        "you're doing your best",
        "you've got this",
        "you are enough",
        "everything happens for a reason",
        "one day at a time",
        "this too shall pass",
        "progress not perfection",
        "focus on what you can control",
        "let go of what no longer serves you",
        "choose compassion",
        "choose peace",
        "sit with your feelings",
        "your trauma does not define you",
        "release what you cannot control",
        "embrace your authentic self",
        "listen to your inner voice",
        "be present in the moment",
        "practice self-care",
        "practice gratitude",
        "you are worthy of healing",
        "you are worthy of love",
        "you are worthy of peace",
        "show up for yourself",
        "hold space for your emotions",
        "i'm here and ready to support you",
        "i’m here and ready to support you",
        "i'm here and ready to help you",
        "i’m here and ready to help you",
        "how are you feeling today",
        "how are you feeling today?",
        "how are you feeling right now",
        

        # Syrupy therapy clichés we want gone
        "i'm really sorry",
        "i am really sorry",
        "i’m really sorry",
        "i'm sorry you're",
        "i am sorry you're",
        "i’m sorry you’re",
        "sorry that you're feeling this way",
        "sorry that you’re feeling this way",
        "sorry that you're feeling",
        "sorry that you’re feeling",

        # "it's okay" validation
        "it's completely okay to feel",
        "its completely okay to feel",
        "it’s completely okay to feel",
        "it's okay to feel",
        "its okay to feel",
        "it’s okay to feel",
        "it's ok to feel",
        "its ok to feel",
        "it’s ok to feel",

        # Not-alone reassurance
        "you're not alone in this",
        "you’re not alone in this",
        "you are not alone in this",
        "you're not alone",
        "you’re not alone",
        "you are not alone",

        # Talk / share invites
        "would you like to talk about",
        "would you like to share",
        "if you'd like to share",
        "if you’d like to share",
        "sometimes just sharing",
        "sometimes just talking about it",

        # I'm here for you
        "i'm here to listen",
        "i am here to listen",
        "i’m here to listen",
        "i'm here for you",
        "i am here for you",
        "i’m here for you",
        "you deserve support",

        # Normalizing clichés
        "everyone goes through things like this",
        "everyone faces challenges",
        "everyone faces challenges in their lives",
        "many people face challenges",
    ]


    # Remove whole sentences that contain any bad phrase (substring match)
    lowered = text.lower()
    for phrase in bad_phrases:
        if phrase in lowered:
            sentences = text.split(".")
            cleaned = []
            for s in sentences:
                if phrase not in s.lower():
                    cleaned.append(s)
            text = ". ".join(cleaned).strip()
            lowered = text.lower()
    # 2) Tone normalizer – small rule-based swaps
    replacements = {
        "Pause before speaking.": "Pause before you respond.",
        "Respond firmly but without harshness.": "Stay firm but stay in control.",
        "Protect your dignity.": "Protect your dignity and keep your center.",
        "Remember who you are.": "Stay grounded.",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    # 3) Strip out full sentences that are therapy clichés
    therapy_patterns = [
        "i'm really sorry to hear",
        "i am really sorry to hear",
        "i'm really sorry that you're feeling this way",
        "i am really sorry that you're feeling this way",
        "it's completely okay to feel",
        "it’s completely okay to feel",
        "it's okay to feel",
        "it’s okay to feel",
        "it's important to acknowledge",
        "it’s important to acknowledge",
        "you're not alone in this",
        "you are not alone in this",
        "you're not alone, and",
        "you are not alone, and",
        "would you like to talk about",
        "would you like to share more",
        "if you'd like to share more",
        "if you’d like to share more",
        "just talking about it can help",
        "just talking about it can provide a little relief",
        "can provide a little relief",
        "sometimes just talking about it",
        "sometimes just sharing can help",
        "take things one step at a time",
        "take it one step at a time",
        "that's completely understandable",
        "that’s completely understandable",
    ]

    sentences = [s.strip() for s in text.split(".") if s.strip()]
    cleaned_sentences = []
    for s in sentences:
        lower_s = s.lower()
        if any(p in lower_s for p in therapy_patterns):
            # Skip canned-therapy sentences entirely
            continue
        cleaned_sentences.append(s)

    if cleaned_sentences:
        text = ". ".join(cleaned_sentences)
        if text and not text.endswith("."):
            text += "."
    else:
        # If we stripped everything, fall back to a simple grounded line
        text = "Alright. Let's slow this down for a second. Tell me what part feels heaviest right now."

    # Strengthen clarity: strip leading/trailing whitespace + double spaces
    text = " ".join(text.split())

    # Style C fallback
    if not text.strip():
        return (
            "Life tests your foundation. Stay steady. "
            "Tell me what needs clarity."
        )

    return text

def enforce_style_governor(text: str) -> str:
    """
    Compatibility wrapper so other modules can call a single entrypoint.
    Right now it just delegates to ground_tone().
    """
    return ground_tone(text)