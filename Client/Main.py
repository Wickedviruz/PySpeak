import sys
import asyncio
import qasync
from PyQt5.QtWidgets import QApplication
from gui import VoiceChatClient

if __name__ == '__main__':
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    client = VoiceChatClient()
    client.show()

    print('Starting client')
    loop.run_forever()
