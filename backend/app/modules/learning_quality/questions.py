"""Original fixed-form placement v1. Approximate course difficulty, not certification."""

# topic, difficulty, prompt, options, correct index
QUESTIONS = [
    (
        "vocabulary_daily",
        "A1",
        "I am thirsty. Could I have a glass of ___?",
        ["water", "bread", "rice"],
        0,
    ),
    ("present_simple", "A1", "My sister ___ to work by bus every day.", ["go", "goes", "going"], 1),
    (
        "past_simple",
        "A2",
        "Yesterday we ___ a film at home.",
        ["watch", "have watched", "watched"],
        2,
    ),
    (
        "vocabulary_context",
        "A2",
        "The train is delayed. It will arrive ___ than planned.",
        ["earlier", "later", "faster"],
        1,
    ),
    (
        "present_perfect",
        "B1",
        "I ___ here since 2020 and still live here.",
        ["have lived", "lived", "am living"],
        0,
    ),
    (
        "conditionals",
        "B1",
        "If I had more time, I ___ another language.",
        ["will learn", "would learn", "learn"],
        1,
    ),
    (
        "reading_detail",
        "B1",
        (
            "Mira usually cycles to work. Today heavy rain made her take the bus. "
            "Why did she change her routine?"
        ),
        ["Her bicycle was broken.", "She moved house.", "The weather was bad."],
        2,
    ),
    (
        "vocabulary_collocation",
        "B2",
        "The researchers could not ___ a conclusion from such limited evidence.",
        ["do", "draw", "give"],
        1,
    ),
    (
        "past_perfect",
        "B2",
        "By the time we reached the station, the train ___.",
        ["has left", "had left", "leaves"],
        1,
    ),
    (
        "reading_inference",
        "B2",
        (
            "A town made bus travel free. Passenger numbers rose, but traffic barely fell: "
            "most new passengers had previously walked. What does this suggest?"
        ),
        [
            "Free buses always reduce traffic.",
            "Most drivers switched to buses.",
            "Higher bus use need not mean fewer car journeys.",
        ],
        2,
    ),
    (
        "inversion",
        "C1",
        "Not until the results were published ___ the scale of the problem.",
        ["we understood", "did we understand", "we did understand"],
        1,
    ),
    (
        "vocabulary_nuance",
        "C1",
        "The findings are tentative: they should be treated as ___.",
        ["provisional", "conclusive", "irrelevant"],
        0,
    ),
]
