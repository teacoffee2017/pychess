import asyncio
from io import StringIO

from gi.repository import Gtk

from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import WHITE, BLACK, LOCAL, RUNNING
from pychess.Utils.LearnModel import LearnModel, LECTURE
from pychess.Utils.TimeModel import TimeModel
from pychess.Utils.Move import parseAny
from pychess.Players.Human import Human
from pychess.perspectives import perspective_manager
from pychess.Savers import fen as fen_loader

__title__ = _("Lectures")

__icon__ = addDataPrefix("glade/panel_book.svg")

__desc__ = _("Study FICS lectures offline")


LECTURES = (
    (1, "lec1.txt", "2...Qh4+ against the King's Gambit", "toddmf"),
    (2, "lec2.txt", "Tactics Training lesson 1# 'Back rank weakness'", "knackie"),
    (3, "lec3.txt", "Denker's Favorite Game", "toddmf"),
    (4, "lec4.txt", "Introduction to the 2.Nc3 Caro-Kann", "KayhiKing"),
    (5, "lec5.txt", "Tactics Training lesson 2# 'Discovered Attack'", "knackie"),
    (6, "lec6.txt", "King's Indian Attack vs. the French", "cissmjg"),
    (7, "lec7.txt", "Rook vs Pawn endgames", "toddmf"),
    (8, "lec8.txt", "The Stonewall Attack", "MBDil"),
    (9, "lec9.txt", "Tactics Training lesson 3# 'Enclosed Kings'", "knackie"),
    (10, "lec10.txt", "The Steinitz Variation of the French Defense", "Seipman"),
    (11, "lec11.txt", "A draw against a Grandmaster", "talpa"),
    (12, "lec12.txt", "Tactics Training lesson 4# 'King in the centre'", "knackie"),
    (13, "lec13.txt", "The Modern Defense", "GMDavies"),
    (14, "lec14.txt", "Tactics Training lesson 5# 'Pulling the king to the open'", "knackie"),
    (15, "lec15.txt", "King's Indian Attack vs. the Caro-Kann", "cissmjg"),
    (16, "lec16.txt", "Introduction to Bughouse", "Tecumseh"),
    (17, "lec17.txt", "Refuting the Milner-Barry Gambit in the French Defense", "Kabal"),
    (18, "lec18.txt", "Tactics Training lesson 6# 'Mating Attack'", "knackie"),
    (19, "lec19.txt", "Closed Sicilian Survey, part 1", "Oren"),
    (20, "lec20.txt", "Hypermodern Magic - A study of the central blockade", "Bahamut"),
    (21, "lec21.txt", "Tactics Training lesson 7# 'Opening / Closing Files'", "knackie"),
    (22, "lec22.txt", "Thoughts on the Refutation of the Milner-Barry", "knackie"),
    (23, "lec23.txt", "Tactics Training lesson 8# 'Opening / Closing Diagonals'", "knackie"),
    (24, "lec24.txt", "King's Indian Attack vs. Other Defenses", "cissmjg"),
    (25, "lec25.txt", "Basic Pawn Endings I", "DAV"),
    (26, "lec26.txt", "Giuoco Piano", "afw"),
    (27, "lec27.txt", "Tactics Training lesson 9# 'Long Diagonals'", "knackie"),
    (28, "lec28.txt", "Secrets of the Flank Attack", "Shidinov"),
    (29, "lec29.txt", "Mating Combinations", "Kabal"),
    (30, "lec30.txt", "Basic Pawn Endings II", "DAV"),
    (31, "lec31.txt", "Grandmaster Knezevic's first FICS lecture", "toddmf"),
)


class Sidepanel():
    def load(self, persp):
        self.persp = persp
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.tv = Gtk.TreeView()

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Id"), renderer, text=0)
        self.tv.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Title"), renderer, text=2)
        self.tv.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Author"), renderer, text=3)
        self.tv.append_column(column)

        self.tv.connect("row-activated", self.row_activated)

        self.store = Gtk.ListStore(int, str, str, str)

        for num, file_name, title, author in LECTURES:
            self.store.append([num, file_name, title, author])

        self.tv.set_model(self.store)
        self.tv.get_selection().set_mode(Gtk.SelectionMode.BROWSE)
        self.tv.set_cursor(0)

        scrollwin = Gtk.ScrolledWindow()
        scrollwin.add(self.tv)
        scrollwin.show_all()

        self.box.pack_start(scrollwin, True, True, 0)
        self.box.show_all()

        return self.box

    def row_activated(self, widget, path, col):
        if path is None:
            return
        else:
            filename = LECTURES[path[0]][1]
            start_lecture_from(filename)


def start_lecture_from(filename, index=None):
    if index is None:
        index = 0

    # connection.client.run_command("examine")
    timemodel = TimeModel(0, 0)
    gamemodel = LearnModel(timemodel)
    gamemodel.set_learn_data(LECTURE, filename, index)

    white_name = black_name = "PyChess"
    p0 = (LOCAL, Human, (WHITE, white_name), white_name)
    p1 = (LOCAL, Human, (BLACK, black_name), black_name)

    perspective = perspective_manager.get_perspective("games")
    asyncio.async(perspective.generalStart(gamemodel, p0, p1))

    def lecture_steps(lecture_file):
        with open(lecture_file, "r") as f:
            for line in f:
                yield line
        return

    lecture_file = addDataPrefix("learn/lectures/%s" % filename)
    steps = lecture_steps(lecture_file)

    @asyncio.coroutine
    def coro(gamemodel, steps):
        exit_lecture = False
        inside_bsetup = False
        paused = False
        moves_played = 0

        KIBITZ, BACKWARD, BSETUP, BSETUP_DONE, FEN, TOMOVE, WCASTLE, BCASTLE, \
            WNAME, BNAME, REVERT, WAIT, MOVE = range(13)

        while True:
            try:
                step = next(steps)
                print(step)

                parts = step.strip().split()

                command = None
                param = ""

                if parts[0] == "k" or parts[0] == "kibitz":
                    command = KIBITZ
                    param = " ".join(parts[1:])
                elif parts[0] == "back":
                    command = BACKWARD
                    param = int(parts[1]) if len(parts) > 1 else 1
                elif parts[0] == "bsetup":
                    if len(parts) == 1:
                        command = BSETUP
                    else:
                        if parts[1] == "done":
                            command = BSETUP_DONE
                        elif parts[1] == "fen":
                            command = FEN
                            param = parts[2]
                        elif parts[1] == "tomove":
                            command = TOMOVE
                            param = "w" if parts[2].lower()[0] == "w" else "b"
                        elif parts[1] == "wcastle":
                            command = WCASTLE
                            param = parts[2]
                        elif parts[1] == "bcastle":
                            command = BCASTLE
                            param = parts[2]
                elif parts[0] == "tomove":
                    command = TOMOVE
                    param = "w" if parts[1].lower()[0] == "w" else "b"
                elif parts[0] == "wname":
                    command = WNAME
                    param = parts[1]
                elif parts[0] == "bname":
                    command = BNAME
                    param = parts[1]
                elif parts[0] == "revert":
                    command = REVERT
                elif len(parts) == 1 and parts[0].isdigit():
                    command = WAIT
                    param = int(parts[0])
                else:
                    command = MOVE
                    param = parts[0]

                if not inside_bsetup and command == BSETUP:
                    inside_bsetup = True
                    pieces = ""
                    color = ""
                    castl = ""
                    ep = ""
                elif inside_bsetup and command == BSETUP_DONE:
                    inside_bsetup = False

                wait_sec = int(param) if command == WAIT else 2

                if inside_bsetup:
                    wait_sec = -1

                while wait_sec >= 0:
                    if gamemodel.lecture_exit_event.is_set():
                        gamemodel.lecture_exit_event.clear()
                        exit_lecture = True
                        break

                    if gamemodel.lecture_skip_event.is_set():
                        gamemodel.lecture_skip_event.clear()
                        paused = False
                        break

                    if gamemodel.lecture_pause_event.is_set():
                        gamemodel.lecture_pause_event.clear()
                        paused = True

                    yield from asyncio.sleep(0.1)
                    if not paused:
                        wait_sec = wait_sec - 0.1

                if exit_lecture:
                    gamemodel.players[0].putMessage("Lecture exited.")
                    break

                if command != WAIT:
                    if command == KIBITZ:
                        gamemodel.players[0].putMessage(param)
                    if command == BACKWARD:
                        gamemodel.undoMoves(param)
                        moves_played -= param
                    if command == MOVE:
                        board = gamemodel.getBoardAtPly(gamemodel.ply)
                        move = parseAny(board, param)
                        gamemodel.curplayer.move_queue.put_nowait(move)
                        moves_played += 1
                    elif command == REVERT:
                        gamemodel.undoMoves(moves_played)
                        moves_played = 0
                    elif command == BNAME:
                        gamemodel.players[BLACK].name = param
                        gamemodel.emit("players_changed")
                    elif command == WNAME:
                        gamemodel.players[WHITE].name = param
                        gamemodel.emit("players_changed")
                    elif command == FEN:
                        pieces = param
                    elif command == TOMOVE:
                        color = param
                    elif command == WCASTLE:
                        if param == "both":
                            castl += "KQ"
                        elif param == "kside":
                            castl += "K"
                        elif param == "qside":
                            castl += "Q"
                    elif command == BCASTLE:
                        if param == "both":
                            castl += "kq"
                        elif param == "kside":
                            castl += "k"
                        elif param == "qside":
                            castl += "q"
                    elif command == BSETUP_DONE:
                        if not castl:
                            castl = "-"
                        if not ep:
                            ep = "-"
                        fen = "%s %s %s %s 0 1" % (pieces, color, castl, ep)

                        curplayer = gamemodel.curplayer
                        gamemodel.status = RUNNING
                        gamemodel.loadAndStart(
                            StringIO(fen),
                            fen_loader,
                            0,
                            -1,
                            first_time=False)
                        curplayer.move_queue.put_nowait("int")
                        gamemodel.emit("game_started")
                        moves_played = 0

            except StopIteration:
                # connection.client.run_command("kibitz That concludes this lecture.")
                break

    asyncio.async(coro(gamemodel, steps))
