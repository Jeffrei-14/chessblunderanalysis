from flask import Flask, request, redirect, url_for, render_template_string
import chess
import chess.pgn
import chess.engine
import os
import tempfile

app = Flask(__name__)

# Configuration
engine_path = "D:\\stockfish-windows-x86-64-avx2\\stockfish\\stockfish.exe"  # Set your Stockfish path
max_depth = 20
max_time = 0.5
blunder_thresh = -500
possible = 5

def get_best_variations(board, engine, max_time, max_depth, possible):
    info = engine.analyse(board, chess.engine.Limit(time=max_time, depth=max_depth), multipv=possible)
    variations = []
    for variation in info:
        if "pv" in variation and variation["pv"]:
            move = variation["pv"][0]
            if board.is_legal(move):
                variations.append(move)
    return variations

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if 'pgn_file' not in request.files:
            return "No file part"
        file = request.files['pgn_file']
        if file.filename == '':
            return "No selected file"
        if file:
            # Save the uploaded PGN to a temp file
            temp_pgn = tempfile.NamedTemporaryFile(delete=False, suffix=".pgn")
            file.save(temp_pgn.name)
            temp_pgn.close()

            # Analyze the uploaded PGN
            results = analyze_pgn(temp_pgn.name)

            os.unlink(temp_pgn.name)  # Delete temp file after processing

            # Render results
            return render_template_string(results_template, results=results)
    
    return render_template_string(upload_template)

def analyze_pgn(pgn_path):
    results = []

    # Load PGN and extract games
    games = []
    with open(pgn_path, 'r') as f:
        game = chess.pgn.read_game(f)
        while game:
            games.append(game)
            game = chess.pgn.read_game(f)

    # Start Stockfish
    engine = chess.engine.SimpleEngine.popen_uci(engine_path)

    for game in games:
        board = game.board()
        event_name = game.headers.get('Event', 'Unknown Event')
        player_white = game.headers.get('White', 'Unknown')
        player_black = game.headers.get('Black', 'Unknown')
        game_result = {"event": event_name, "white": player_white, "black": player_black, "blunders": []}

        for move in game.mainline_moves():
            board.push(move)
            info = engine.analyse(board, chess.engine.Limit(time=max_time))
            score = info["score"].relative.score() if not info["score"].is_mate() else None
            
            if score is not None and score <= blunder_thresh:
                best_variations = get_best_variations(board, engine, max_time, max_depth, possible)
                blunder_info = {
                    "fen": board.fen(),
                    "move": move.uci(),
                    "score": score,
                    "alternatives": [v.uci() for v in best_variations]
                }
                game_result["blunders"].append(blunder_info)
        
        results.append(game_result)

    engine.close()
    return results

# Upload Template
upload_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Upload PGN for Blunder Detection Analysis</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Poppins', sans-serif;
            background-color: #f8f9fa;
            padding-top: 50px;
        }
        .container {
            max-width: 500px;
        }
        .btn-primary {
            width: 100%;
        }
        h1 {
            font-weight: 600;
            margin-bottom: 30px;
            text-align: center;
        }
    </style>
</head>
<body>
<div class="container">
    <h1>Upload a PGN File</h1>
    <form method="post" enctype="multipart/form-data" class="card p-4 shadow">
        <div class="mb-3">
            <input type="file" class="form-control" name="pgn_file" accept=".pgn" required>
        </div>
        <button type="submit" class="btn btn-primary">Upload and Analyze</button>
    </form>
</div>
</body>
</html>
"""

# Results Template
results_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Blunder Detection Analysis Results</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Poppins', sans-serif;
            background-color: #f8f9fa;
            padding-top: 30px;
        }
        .game-card {
            margin-bottom: 30px;
        }
        h1 {
            font-weight: 600;
            margin-bottom: 30px;
            text-align: center;
        }
    </style>
</head>
<body>
<div class="container">
    <h1>Chess Blunder Detection And Analysis Results</h1>
    {% for game in results %}
        <div class="card game-card shadow-sm">
            <div class="card-body">
                <h5 class="card-title">{{ game.event }}</h5>
                
                {% if game.blunders %}
                    <ul class="list-group list-group-flush">
                    {% for blunder in game.blunders %}
                        <li class="list-group-item">
                            <strong>Blunder Move:</strong> {{ blunder.move }}<br>
                            <strong>Score:</strong> {{ blunder.score }}<br>
                            <strong>Best Alternatives:</strong> {{ blunder.alternatives }}
                        </li>
                    {% endfor %}
                    </ul>
                {% else %}
                    <p class="card-text mt-2">No blunders found in this game.</p>
                {% endif %}
            </div>
        </div>
    {% endfor %}
    <div class="text-center">
        <a href="/" class="btn btn-primary">Upload Another PGN</a>
    </div>
</div>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(debug=True)
