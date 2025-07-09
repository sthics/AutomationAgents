# Notion AI Agent

A simple AI agent that connects to Notion, Gmail, and Spotify, using local models to answer questions and automate tasks with your data.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/notion-ai-agent.git
    cd notion-ai-agent
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up your environment variables:**
    -   Create a `.env` file in the root directory.
    -   Add your Notion and Spotify credentials to the `.env` file:
        ```
        NOTION_TOKEN=your-notion-token
        SPOTIFY_CLIENT_ID=your-spotify-client-id
        SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
        ```
    -   For Gmail, place your `gmail_credentials.json` in the `Gmail_Agent/` directory (or update the path in the code if needed).

4.  **Run the agents:**
    -   **Notion Agent:**
        ```bash
        python notion_agent.py
        ```
    -   **Gmail Agent:**
        ```bash
        python Gmail_Agent/gmail_agent.py
        ```
    -   **Spotify Agent:**
        ```bash
        python Spotify_Agent/spotify_agent.py
        ```

Each agent provides an interactive CLI for managing and querying your data. Follow the on-screen instructions to use each agent's features.
