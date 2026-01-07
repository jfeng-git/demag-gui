"""程序的入口点"""

import sys

def main():
    """main function"""
    print("starting gui ...")
    # 启动GUI或CLI
    from .app import DemagApp
    app = DemagApp()
    return app.run()

if __name__ == "__main__":
    sys.exit(main())