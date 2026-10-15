# Web Application Exercise

A little exercise to build a web application following an agile development process. See the [instructions](instructions.md) for more detail.

## Product vision statement

### Roommate Share is a mobile-friendly web app that lets roommates keep track of the food and household items in their home, see who owns what, and know at a glance which items are fair game to share.

## User stories

### [Link to user stories](https://github.com/software-students-fall2026/web-app-exercise-goodTeam/issues)

## Steps necessary to run the software

See instructions. Delete this line and place instructions to download, configure, and run the software here.

## Task boards

See instructions. Delete this line and place a link to the task boards here.

## Steps necessary to run the software

1. Clone the repo and enter it:
   ```bash
   git clone git@github.com:software-students-fall2026/web-app-exercise-goodTeam.git
   cd web-app-exercise-goodTeam
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

3. Start MongoDB in Docker:
   ```bash
   docker run --name mongo -p 27017:27017 \
     -e MONGO_INITDB_ROOT_USERNAME=admin \
     -e MONGO_INITDB_ROOT_PASSWORD=secret \
     -d mongo:7
   ```

4. Create a `.env` file from the example (`cp env.example .env`) with:
   ```
   DB_URI=mongodb://admin:secret@localhost:27017/?authSource=admin
   DB_NAME=roommate_share
   PORT=8081
   HOST=localhost
   FLASK_SECRET_KEY=any-long-random-string
   ```

5. Run the app and open http://localhost:8081:
   ```bash
   python app.py
   ```
