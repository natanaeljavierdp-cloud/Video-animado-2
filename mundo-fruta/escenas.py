# Definición de las 8 escenas de "Mundo Fruta" (imagen + animación + subtítulos)

ESTILO = (
    "Vertical 9:16 cinematic frame, 3D animated feature film style (high-end family animation), "
    "dark secret room, round wooden table, a single hanging pendant lamp with warm golden light, "
    "soft drifting smoke, strong chiaroscuro, subtle film grain, shallow depth of field. "
    "Cartoon fruit characters with cartoon faces and NO human noses. "
    "Characters must look IDENTICAL to the reference images (same colors, outfits, accessories, proportions). "
    "No text, no letters, no captions, no watermark anywhere in the image."
)

REVISTA = (
    "a magazine whose cover is a circular red, black and white illustration with rockets, robots, "
    "coins and a red sun (the cover has no readable text)"
)

PERS = {
    "don_pina": "Don Piña: a pineapple with a golden crown with rubies, black suit with golden pinstripes, golden tie, gold watch",
    "big_apple": "Big Apple: a red apple with sunglasses resting on top of his head, navy blue suit, red tie",
    "mandarina": "Mandarina: a mandarin orange with a green leaf, wine-red suit with golden buttons",
    "klukva": "Klukva: a red cranberry with a grey fur ushanka hat with ear flaps, dark grey suit, long black overcoat",
    "las_uvas": "Las Uvas: a bunch of purple grapes, each grape has its own little face and mini suit with a tie of a different color (red, purple, yellow, blue, green; one grape wears glasses)",
}

ESCENAS = [
    {
        "n": 1,
        "pers": ["don_pina", "big_apple", "mandarina", "klukva", "las_uvas"],
        "imagen": f"All five characters seated around the round wooden table under the hanging lamp. "
                  f"Don Piña stands at the head of the table holding {REVISTA} just above the table, about to drop it. "
                  f"The others look at him seriously.",
        "video": "Don Piña drops the magazine onto the table with a soft thud, smoke swirls in the lamp light. "
                 "Don Piña speaks in a deep, slow, elegant Latin American Spanish voice: "
                 "\"Señores… la portada ya salió. Y nadie la entendió.\" "
                 "Only Don Piña's mouth moves; the other characters stay silent with closed mouths, only small reactions.",
        "subs": [(1.0, 4.2, "Señores… la portada ya salió."), (4.4, 7.6, "Y nadie la entendió.")],
    },
    {
        "n": 2,
        "pers": ["big_apple"],
        "imagen": f"Close-up of Big Apple at the table, laughing and pointing at the rockets on {REVISTA} lying on the table.",
        "video": "Big Apple laughs loudly and taps the rockets on the magazine cover. He speaks in Spanish with a strong "
                 "American accent, a cheerful salesman voice: "
                 "\"¡Pusieron cohetes! En 2027 le vendemos la Luna a todos.\" Only Big Apple speaks.",
        "subs": [(0.8, 3.6, "¡Pusieron cohetes!"), (3.8, 7.6, "En 2027 le vendemos la Luna a todos.")],
    },
    {
        "n": 3,
        "pers": ["mandarina"],
        "imagen": "Mandarina seated at the table holding a tablet that shows small cartoon robots; the cool blue glow "
                  "of the tablet lights his face from below, contrasting with the warm golden lamp light.",
        "video": "Mandarina slowly swipes the tablet, blue light on his face, and speaks in a calm, calculating Latin American "
                 "Spanish voice: \"Los robots salieron también. Tranquilos… todos son míos.\" "
                 "He gives a small sly smile at the end. Only Mandarina speaks.",
        "subs": [(0.8, 4.0, "Los robots salieron también."), (4.3, 7.6, "Tranquilos… todos son míos.")],
    },
    {
        "n": 4,
        "pers": ["klukva"],
        "imagen": f"Klukva leaning over the table, sliding one finger across {REVISTA}, hard film-noir side lighting "
                  f"cutting across his face, eyes looking straight into the camera.",
        "video": "Klukva slowly slides his finger across the magazine cover, film-noir side light, then looks straight at "
                 "the camera and speaks in Spanish with a Russian accent, deep and mysterious voice: "
                 "\"Aquí hay un símbolo que nadie ha visto… Yo sí.\" Only Klukva speaks.",
        "subs": [(0.8, 5.0, "Aquí hay un símbolo que nadie ha visto…"), (5.3, 7.6, "Yo sí.")],
    },
    {
        "n": 5,
        "pers": ["las_uvas"],
        "imagen": "Las Uvas on the table, the little grapes arguing animatedly with each other; one grape with glasses, "
                  "one grape asleep.",
        "video": "The grapes argue with distinct voices in Latin American Spanish. The grape with the red tie: "
                 "\"¿Y quién paga la deuda?\" The grape with the purple tie: \"¡Votemos!\" The grape with glasses: "
                 "\"¡Mejor otra reunión!\" At the end, the sleeping grape snores loudly. "
                 "Only the grape currently speaking moves its mouth.",
        "subs": [(0.5, 2.8, "¿Y quién paga la deuda?"), (3.0, 4.4, "¡Votemos!"), (4.6, 6.6, "¡Mejor otra reunión!"),
                 (6.8, 8.0, "(ronquido)")],
    },
    {
        "n": 6,
        "pers": ["big_apple", "mandarina", "klukva"],
        "imagen": f"Big Apple, Mandarina and Klukva together at the table looking down at {REVISTA}; "
                  f"Big Apple points at a tiny pill drawn on the cover. In the dark background, a golden crown "
                  f"glints faintly in the shadows.",
        "video": "Big Apple points at a small pill on the magazine cover and says in Spanish with an American accent: "
                 "\"¿Y quién puso esa pastillita ahí?\" Then all three slowly turn their heads toward a golden crown "
                 "shining in the shadows. Only Big Apple speaks; Mandarina and Klukva keep their mouths closed.",
        "subs": [(0.8, 4.0, "¿Y quién puso esa pastillita ahí?")],
    },
    {
        "n": 7,
        "pers": ["don_pina"],
        "imagen": "Low-angle shot of Don Piña seated at the head of the table, hands steepled together, "
                  "the lamp above him, imposing and elegant.",
        "video": "Low-angle shot. Don Piña steeples his hands, the lamp light slowly dims. He speaks in a deep, slow, "
                 "elegant Latin American Spanish voice: \"Yo. Esta portada no predice el futuro… lo anuncia.\" "
                 "Only Don Piña speaks.",
        "subs": [(0.8, 2.0, "Yo."), (2.3, 5.8, "Esta portada no predice el futuro…"), (6.0, 7.8, "…lo anuncia.")],
    },
    {
        "n": 8,
        "pers": ["don_pina", "big_apple", "mandarina", "klukva", "las_uvas"],
        "imagen": f"Close-up on {REVISTA} lying on the table, with the five characters' startled faces around the edges "
                  f"of the frame in the lamp light. In one corner of the cover, a subtle golden silhouette of a banana.",
        "video": "Slow push-in on the magazine cover; the golden banana silhouette in the corner begins to glow. "
                 "All five characters gasp and jump back, frightened. The hanging lamp flickers and everything fades to "
                 "black. An off-screen whispering voice in Latin American Spanish: "
                 "\"Y en 2027… llega alguien que no invitamos.\" None of the characters speak.",
        "subs": [(3.0, 5.4, "Y en 2027…"), (5.5, 8.0, "…llega alguien que no invitamos.")],
    },
]

NEGATIVO_VIDEO = (
    "text, subtitles, captions, letters, watermark, English speech, scene cuts, human nose, "
    "weapons, violence, extra characters"
)
