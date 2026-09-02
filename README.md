# 🎧 AI Collaborative Music Playlist API

A multi-agent AI system that generates curated music playlists and verifies them against Spotify (with async orchestration).

This project includes:
- FastAPI backend
- MongoDB Atlas integration
- Multi-agent AI system
- Spotify verification
- Docker support
- uv dependency management

---

# 🚀 What This Project Does

1. Receives a prompt to generate a playlist
2. Multiple specialized AI agents generate recommendations
3. Recommendations are merged and deduplicated
4. The list is reduced to 35–50 tracks
5. Tracks are verified against Spotify
6. The final playlist is returned (and optionally stored in MongoDB)

---

# ⚙️ Requirements

- Python 3.13
- uv (dependency manager)
- MongoDB Atlas account
- Spotify Developer account
- OpenAI API key
- Docker (optional)

---

# 🔑 Environment Variables

Create a .env file in the project root:

OPENAI_API_KEY=your_openai_key

SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8080/callback

MONGO_URI=mongodb+srv://USER:PASSWORD@CLUSTER.mongodb.net/?appName=APPNAME
MONGO_DB=DB_NAME

⚠️ Do NOT commit your .env file.

---

# ▶️ Run Locally

1. Install uv (if not installed)

pip install uv

2. Install dependencies

uv sync

3. Start the API

uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

4. Test in browser

http://localhost:8000/health
http://localhost:8000/docs

---

# 🐳 Run with Docker

1. Build image

docker build -t ai-playlist-api .

2. Run container

docker run --rm -p 8000:8000 --env-file .env ai-playlist-api

API will be available at:

http://localhost:8000
http://localhost:8000/docs

---

# 📡 Example Requests

Health Check:

curl http://localhost:8000/health

Generate Playlist:

curl -X POST http://localhost:8000/playlists/generate \
-H "Content-Type: application/json" \
-d '{
  "user_id": "YOUR_USER_ID",
  "prompt": "90s alternative rock deep cuts",
  "min_songs": 35,
  "max_songs": 50,
  "title": "90s Road Trip",
  "description": "Deep cuts and classics"
}'

---

# 🧪 Debugging Tips

If Docker doesn't connect to MongoDB Atlas:

1. Check Atlas IP allowlist
2. Verify MONGO_URI is correct
3. Make sure certifi and dnspython are installed
4. Check container logs:

docker ps
docker logs <container_id>

---

# 🚀 Production Notes

For production:

uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

Consider running behind NGINX or a cloud load balancer.

---

# 🔮 Future Improvements

- Create Spotify playlists automatically
- Add authentication (JWT/Firebase)
- Rank tracks using Spotify audio features
- Cache verification results
- Add frontend (web/mobile app)
- Deploy to cloud (AWS, GCP, Azure, Railway, etc.)

---

Made with FastAPI, OpenAI, Spotify API, MongoDB Atlas, and Docker.
