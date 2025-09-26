import sqlite3
import os
# DB pathing
basedir = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(basedir, 'database.db')

def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")


# Database helpers
def connect_db():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at '{DB_PATH}'. Put database.db next to this script or update DB_PATH.")
    return sqlite3.connect(DB_PATH)

def get_available_genres():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT Genre_name FROM Genre ORDER BY Genre_name;")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows

def get_available_years():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT Year FROM Movie ORDER BY Year DESC;")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows

def fetch_all_movies():
    """Return all movies with their concatenated genres."""
    conn = connect_db()
    cur = conn.cursor()
    query = """
      SELECT Movie.Id, Movie.Name, Movie.Year, Movie.Rating,
             GROUP_CONCAT(Genre.Genre_name, ', ') AS Genres
      FROM Movie
      LEFT JOIN Movie_Genre ON Movie.Id = Movie_Genre.Movie_Id
      LEFT JOIN Genre ON Genre.Id = Movie_Genre.Genre_Id
      GROUP BY Movie.Id
      ORDER BY Movie.Year DESC, Movie.Name ASC;
    """
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "year": r[2], "rating": r[3], "genres": r[4] or ""} for r in rows]

def apply_filters(selected_genres, selected_years, min_rating, require_all_genres=False):
    """
    selected_genres : list of strings (genre names, case-insensitive)
    selected_years  : list of ints
    min_rating      : float or None
    require_all_genres: if True, only return movies that have ALL selected_genres
                        if False (default), return movies that have ANY of selected_genres
    """
    conn = connect_db()
    cur = conn.cursor()

    base = """
      SELECT Movie.Id, Movie.Name, Movie.Year, Movie.Rating,
             GROUP_CONCAT(Genre.Genre_name, ', ') AS Genres
      FROM Movie
      LEFT JOIN Movie_Genre ON Movie.Id = Movie_Genre.Movie_Id
      LEFT JOIN Genre ON Genre.Id = Movie_Genre.Genre_Id
      WHERE 1=1
    """
    params = []

    # Genre filter 
    if selected_genres:
        placeholders = ",".join("?" for _ in selected_genres)
        # restrict rows to those genres (we count later if require_all_genres)
        base += f" AND lower(Genre.Genre_name) IN ({placeholders})"
        params.extend([g.lower() for g in selected_genres])

    # Year filter
    if selected_years:
        placeholders = ",".join("?" for _ in selected_years)
        base += f" AND Movie.Year IN ({placeholders})"
        params.extend(selected_years)

    # Rating filter
    if min_rating is not None:
        base += " AND Movie.Rating >= ?"
        params.append(min_rating)

    # Group + HAVING 
    base += " GROUP BY Movie.Id"

    if selected_genres and require_all_genres:
        base += " HAVING COUNT(DISTINCT lower(Genre.Genre_name)) >= ?"
        params.append(len(selected_genres))

    base += " ORDER BY Movie.Year DESC, Movie.Name ASC;"

    cur.execute(base, params)
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "year": r[2], "rating": r[3], "genres": r[4] or ""} for r in rows]

# Display if movie not found
def display_movies(movie_list):
    clear_terminal()
    if not movie_list:
        print("\n⚠️  No movies found with your filters.\n")
        return
    print()
    for m in movie_list:
        print(f"🎬 {m['title']} ({m['year']}) - {m['genres']} | ⭐ {m['rating']}")
    print()

# Menus
def prompt_choose_genres(current_selection):
    """Let user pick genres by name or by index from available list."""
    available = get_available_genres()
    if not available:
        print("No genres found in Database.")
        return []

    print("\nAvailable genres:")
    for i, g in enumerate(available, start=1):
        print(f"  {i}. {g}")

    print("\nYou may only choose either one:")
    print("- Enter genre names separated by commas (e.g. Action, Comedy)")
    print("- OR enter indices separated by commas (e.g. 1,3)")
    print("")
    print("Please press Enter to keep current selection")
    raw = input(f"Selected genres [{', '.join(current_selection) if current_selection else 'none'}]: ").strip()
    if raw == "":
        return current_selection

    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    if tokens and all(tok.isdigit() for tok in tokens):
        chosen = []
        for tok in tokens:
            idx = int(tok) - 1
            if 0 <= idx < len(available):
                chosen.append(available[idx])
            else:
                print(f"Index {tok} is out of range, ignoring.")
        return chosen
    else:
        chosen = []
        lower_map = {g.lower(): g for g in available}
        for tok in tokens:
            key = tok.lower()
            if key in lower_map:
                chosen.append(lower_map[key])
                clear_terminal()
            else:
                clear_terminal()
                print(f"Genre '{tok}' not found — ignoring.")
        return chosen

def prompt_choose_years(current_selection):
    available = get_available_years()
    if not available:
        clear_terminal()
        print("No years found in DB.")
        return []
    clear_terminal()
    print("\nAvailable years:")
    print(", ".join(str(y) for y in available))

    raw = input(f"Enter years separated by commas (current: {', '.join(str(y) for y in current_selection) if current_selection else 'none'}): ").strip()
    if raw == "":
        return current_selection

    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    years = []
    for tok in tokens:
        if tok.isdigit():
            clear_terminal()
            year = int(tok)
            if year in available:
                years.append(year)
            else:
                print(f"Ignoring unavailable year '{year}'.")
        else:
            clear_terminal()
            print(f"Ignoring invalid year '{tok}'.")
    return years

def filter_menu():
    selected_genres = []
    selected_years = []
    min_rating = None
    genre_match_all = False  # False = ANY (OR), True = ALL (AND)

#Filters 
    while True:
        print("\n--- Filter Menu ---")
        print(f" Current genres: {selected_genres or 'none'}")
        print(f" Current years : {selected_years or 'none'}")
        print(f" Minimum rating: {min_rating if min_rating is not None else 'none'}")
        print(f" Genre match mode: {'ALL (movie must have all selected genres)' if genre_match_all else 'ANY (movie has any selected genre)'}")
        print("-------------------")
        print("1. Choose genres")
        print("2. Choose years")
        print("3. Set minimum rating")
        print("4. Toggle genre match mode (Any / All)")
        print("5. Show results (apply filters)")
        print("6. Clear filters")
        print("7. Back to main menu")
        print("-------------------")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            clear_terminal()
            selected_genres = prompt_choose_genres(selected_genres)

        elif choice == "2":
            clear_terminal()
            selected_years = prompt_choose_years(selected_years)

        elif choice == "3":
            clear_terminal()
            raw = input("Enter minimum rating (e.g. 8.0) or blank to keep current: ").strip()
            if raw == "":
                pass
            else:
                try:
                    min_rating = float(raw)
                except ValueError:
                    print("Invalid rating input — please use a number like 7.5")

        elif choice == "4":
            clear_terminal()
            genre_match_all = not genre_match_all
            print(f"Genre match mode set to: {'ALL' if genre_match_all else 'ANY'}")

        elif choice == "5":
            clear_terminal()
            print("\n🎬 Filtered Results:\n")
            results = apply_filters(selected_genres, selected_years, min_rating, require_all_genres=genre_match_all)
            display_movies(results)

        elif choice == "6":
            selected_genres = []
            selected_years = []
            min_rating = None
            clear_terminal()
            print("Filters cleared!")

        elif choice == "7":
            clear_terminal()
            break

        else:
            clear_terminal()
            print("Invalid choice, try again!")

# Select Menu
def main_menu():
    print("=" * 60)
    print("🎬  Welcome to the Movie Selector  🎬")
    print("=" * 60)
    print("1. View all movies")
    print("2. Filter movies (choose multiple filters)")
    print("3. Exit")
    print("=" * 60)

#Exit
def main():
    clear_terminal()
    try:
        while True:
            main_menu()
            ch = input("Enter your choice (1-3): ").strip()
            if ch == "1":
                clear_terminal()
                movies = fetch_all_movies()
                display_movies(movies)
            elif ch == "2":
                clear_terminal()
                filter_menu()
            elif ch == "3":
                print("\nThank you for using Movie Selector! Goodbye 👋\n")
                break
            else:
                clear_terminal()
                print("Invalid choice, try again.")
        #Error Handling for DB Issues
    except FileNotFoundError as e: 
        print("ERROR:", e)
    except sqlite3.OperationalError as e:
        print("Database error:", e)
        print("Check table/column names and ensure the DB matches the expected schema.")
    except Exception as e:
        print("Unexpected error:", e)

if __name__ == "__main__":
    main()