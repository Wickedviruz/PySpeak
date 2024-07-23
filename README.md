# **PySpeak**

**PySpeak** is a VoIP (Voice over IP) application that allows users to communicate via voice and text in real time. Built with Python and PyQt, PySpeak offers a modern and user-friendly GUI for clients to connect to servers and participate in voice chats. This project is inspired by and aims to replicate features of TeamSpeak. Please note that PySpeak is in an early development stage.

## **Features**

- **Client and Server**: Are under development, client-server architecture for real-time communication.
- **Voice Chat**: Participate in real-time voice chats with other users.
- **Text Chat**: Send and receive text messages.
- **Settings**: Customize audio settings, microphone, and speaker volume.
- **Bookmarks**: Manage and save server bookmarks for quick access.
- **Change Log**: View the changelog for updates and new features.

## **Installation**

1. **Clone the repository**:
    ```sh
    git clone https://github.com/wickedviruz/pyspeak.git
    cd pyspeak
    ```

2. **Create and activate a virtual environment**:
    ```sh
    python -m venv venv
    source venv/bin/activate    # On Windows use `venv\Scripts\activate`
    ```

3. **Install the dependencies**:
    ```sh
    pip install -r requirements.txt
    ```

4. **Initialize the database**:
    ```sh
    python DB_init.py
    ```

## **Usage**

1. **Run the PySpeak client**:
    ```sh
    python gui.py
    ```

2. **Connecting to a Server**:
    - Open the client.
    - Click on `Connections` -> `Connect`.
    - Enter the server address, password, and your nickname.
    - Click `Connect`.

3. **Managing Bookmarks**:
    - Click on `Bookmarks` -> `Manage Bookmarks`.
    - Add, edit, or remove bookmarks as needed.

4. **Adjusting Settings**:
    - Click on `Tools` -> `Settings`.
    - Adjust playback and capture settings as needed.

## **Development**

Contributions are welcome! Feel free to open issues and submit pull requests.

1. **Fork the repository**.
2. **Create a new branch**:
    ```sh
    git checkout -b feature-branch
    ```

3. **Make your changes and commit them**:
    ```sh
    git commit -m "Description of changes"
    ```

4. **Push to your fork and submit a pull request**:
    ```sh
    git push origin feature-branch
    ```

## **License**

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## **Acknowledgements**

- **PyQt**: For the graphical user interface.
- **websockets**: For WebSocket support.
- **pyaudio**: For handling audio input and output.

## **Contact**

For any questions or suggestions, please open an issue or contact [johan.ivarsson@live.se].
