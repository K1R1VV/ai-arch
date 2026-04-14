GENRE_TO_CODE = {
    "Action": 0,
    "Comedy": 1,
    "Drama": 2,
    "Sci-Fi": 3,
    "Horror": 4
}

DEFAULT_CODE = 0

def encode_genre(genre: str) -> int:
    if isinstance(genre, int):
        return genre
    clean = str(genre).strip().title()
    return GENRE_TO_CODE.get(clean, DEFAULT_CODE)