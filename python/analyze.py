#!python3.10
# coding: shift_jis

import os
import sys
import copy
import mido
import collections
from hashlib import sha256
from enum import IntEnum, auto

#================
# 定数
#================
# SMFの最大トラック数
SMF_TRACK_MAXCOUNT = 16
# コントロールチェンジの番号
CONTROL_RPN_DATA_MSB = 6
CONTROL_MAINVOLUME = 7
CONTROL_PANPOT = 10
CONTROL_EXPRESSION = 11
CONTROL_RPN_LSB = 100
CONTROL_RPN_MSB = 101


# ディレイと認める最大のノートオン間隔（拍数単位）
DELAY_MAX_BEAT = 0.9999
# ディレイ関係スコアがこの値以上だったら記録
DELAY_RELATION_SCORE_THRESHOLD = 0.9

# 付属情報のデフォルト値
TEMPO_DEFAULT = 500000 #BPM120
PROGRAM_DEFAULT = 0
PBSENS_DEFAULT = 2
PITCH_DEFAULT = 0
PAN_CENTER = 64
PAN_DEFAULT = PAN_CENTER
MAINVOLUME_DEFAULT = 100
EXPRESSION_DEFAULT = 127

# DiscStationの号数
ISSUE_MIN = 12
ISSUE_MAX = 27

#================
# クラス
#================
class SurvayTargetMessages:
    """調査対象となる、付属する情報（音色等）"""
    # 基本的に、以下の3つの情報を保持する。
    # ・テンポ
    # ・音色
    # ・ピッチベンドセンシティビティ
    # ・ピッチベンド
    # ・パンポット
    # ・メインボリューム
    # ・エクスプレッション
    def __init__(self):
        self.tempo = None
        self.program = None
        self.pbsens = 2
        self.pitch = None
        self.pan = None
        self.mainVol = None
        self.express = None

    def __str__(self):
        return f"prg:{self.program}, pit:{self.pitch}, pan:{self.pan}"

class MidiMsgInfo:
    """MIDIメッセージをパックしたもの（絶対時刻での発生タイミングを保持。
        オプションで付属情報、先行／後続する音を保持）"""
    def __init__(self, _msg: mido.Message, _tick: int, _addInfo: SurvayTargetMessages =None):
        self.msg = _msg
        self.tick = _tick
        self.addInfo = copy.deepcopy(_addInfo)
        self.following = None
        self.preceding = None
    
    def __str__(self):
        return f"AbsTick {self.tick} <{self.msg}>"


#================
# MIDI関連の汎用関数
#================
# midoのMetaMessageオブジェクトから、shift_jisで文字列を取り出す関数
def getTextFromMetaMessage(_msg: mido.MetaMessage):
    try:
        text = _msg.bin()[3:].decode('shift_jis')
    except UnicodeDecodeError:
        text = _msg.bin()[3:]
    return text

# SMFフォーマット1を0に変換する関数
def SMF1to0(_midOrg: mido.MidiFile):
    # フォーマット確認
    if (_midOrg.type != 1):
        print("[Error] SMF format != 1")
        return _midOrg

    # 変換
    midCnv = mido.MidiFile(type=0)
    midCnv.add_track()
    midCnv.tracks[0] = mido.merge_tracks(_midOrg.tracks)

    return midCnv

# SMFフォーマット0を1に変換する関数
# 0トラック目にすべてのメタメッセージ、
# n（n=1~16）トラック目にnチャンネルの情報すべてが入る
# 総Tick数を取得
def SMF0to1AndGetTotalTicks(_midOrg: mido.MidiFile):
    # フォーマット確認
    if (_midOrg.type != 0):
        print("[Error] SMF format != 0")
        return _midOrg

    midCnvTrackCount = SMF_TRACK_MAXCOUNT + 1
    midCnv = mido.MidiFile(type=1)
    midCnv.ticks_per_beat = _midOrg.ticks_per_beat #ヘッダ設定
    for _ in range (midCnvTrackCount):
        midCnv.add_track()
    # 変換のために記録するTick数
    tickInTrack = [0] * midCnvTrackCount # 変換後SMFのあるトラック内において、現状最後尾にあるイベントが発生したタイミング
    tickGlobal = 0 # 全体で進んだTick数を記録
    # sysexの有無
    midCnv.hasSysex = False

    # 変換
    for msg in _midOrg.tracks[0]:
        # Tickを進める
        tickGlobal += msg.time
        # メタメッセージ・システムエクスクルーシブ
        if (msg.is_meta or (msg.type == "sysex")):
            # トラック0へ格納
            msgNew = msg.copy(time = tickGlobal - tickInTrack[0])
            midCnv.tracks[0].append(msgNew)
            tickInTrack[0] = tickGlobal

            # sysexがある場合記録
            if (msg.type == "sysex"):
                midCnv.hasSysex = True
                print(f"[Info] SysEx exist: {msg}")
        # メタメッセージ以外（チャンネル指定がある）
        else:
            ch = msg.channel + 1
            msgNew = msg.copy(time = tickGlobal - tickInTrack[ch])
            midCnv.tracks[ch].append(msgNew)
            tickInTrack[ch] = tickGlobal
    
    midCnv.totalTicks = tickGlobal
    
    return midCnv

# 曲名表示
def getSequenceName(_midData: mido.MidiFile):
    for msg in _midData.tracks[0]:
        if (msg.type == "track_name"):
            return getTextFromMetaMessage(msg)

# 拍子取得
def getTimeSignature(_midData: mido.MidiFile):
    timeSigNume = 4
    timeSigDeno = 4
    for msg in _midData.tracks[0]:
        # 拍子の情報
        if (msg.type == "time_signature"):
            timeSigNume = msg.numerator
            timeSigDeno = msg.denominator
            if (msg.notated_32nd_notes_per_beat != 32/4):
                print(f"[Error] Irregular notated_32nd_notes_per_beat: {msg.notated_32nd_notes_per_beat}")
            break
    return (timeSigNume, timeSigDeno)


#================
# 分析関数（部品）
#================
# セクション開始小節取得
def getSectionStartBars(_midData: mido.MidiFile, _ticksPerBar: int):
    sectionStartBars = [1]

    for i, track in enumerate(_midData.tracks[1:], start=1):
        globalTick = 0 #トラック内で何Tick進んだか
        currentProgram = 0 #現在のプログラム（音色）
        noteOnExistPre = False #トラック内でノートオンがあったとき、まずこのフラグをTrueにする
        noteOnExist = False #noteOnExistPreがTrueになった後、1Tick以上経ったらこのフラグをTrueにする
        # メッセージ走査
        for msg in track:
            globalTick += msg.time
            if (noteOnExistPre and msg.time > 0):
                noteOnExist = True
            # プログラムチェンジ
            if (msg.type == "program_change"):
                if (noteOnExist and currentProgram != msg.program):
                    # プログラムチェンジ以前にノートオンが1つでも存在する（＝持ち替えにあたる）なら、
                    # チェンジのあったタイミングの最寄りの小節区切りを記録
                    startPointTmp = round(globalTick / _ticksPerBar) + 1
                    if (startPointTmp not in sectionStartBars):
                        sectionStartBars.append(startPointTmp)
                currentProgram = msg.program
            # ノートオン
            elif (msg.type == "note_on"):
                noteOnExistPre = True
    sectionStartBars.sort()
    sectionStartBars.append(sys.maxsize)
    return sectionStartBars

# MidiMessageWithAbsTimeの配列（時系列順）を受け取り、正味ノートオン数を求める
# 正味ノートオン数とは、同時のノートオンを1と数えた際の、ノートオンの数
def getNetNoteCount(_MidiMessageWithAbsTimeList):
    tickTmp = -1
    result = 0
    for msgWithAbsTime in _MidiMessageWithAbsTimeList:
        if (tickTmp != msgWithAbsTime.tick):
            result += 1
            tickTmp = msgWithAbsTime.tick
    return result

# ノートオンの情報を抽出し、noteOnInfoにまとめて返す
def extractNoteOnInfo(
        _midData: mido.MidiFile,
        _sectionStartBars,
        _ticksPerBar: int
):
    # ノートオン情報を格納する三次元配列
    noteOnInfo = [[[] for j in range(len(_midData.tracks))] for i in range(len(_sectionStartBars))]

    # テンポ命令を抽出
    tempoMsgInfos = []
    if (True):
        # トラック内で何Tick進んだか
        globalTick = 0
        # 指揮トラック内のメッセージを走査
        for msg in _midData.tracks[0]:
            # トラック内Tickを進める
            globalTick += msg.time
            # テンポ設定
            if (msg.type == "set_tempo"):
                tempoMsgInfos.append(MidiMsgInfo(msg, globalTick))
    
    # 各トラックから、ノートオン（ベロシティ0は除く）の情報を抽出
    # 同時に、音色・ピッチベンド・パン情報を付属情報として記録
    for i, track in enumerate(_midData.tracks[1:], start=1):
        # リズムトラックは無視
        if (i == 10):
            continue

        # トラック内で何Tick進んだか
        globalTick = 0
        # 現在のセクション番号
        currentSectionIndex = 0
        # 現在の付属情報
        currentAddInfo = SurvayTargetMessages()
        # RPN用の一時変数
        tmpRPN = [-1, -1]
        tmpRPNData = [-1, -1]

        # トラック内のメッセージを走査
        for msg in track:
            # トラック内Tickを進める
            globalTick += msg.time
            # セクションの切り替わりに到達したら、セクション番号を更新
            if (globalTick >= _sectionStartBars[currentSectionIndex + 1] * _ticksPerBar):
                currentSectionIndex += 1
            # テンポ命令に到達したら、currentAddInfoを更新
            for tempoMsgInfo in tempoMsgInfos:
                if (globalTick >= tempoMsgInfo.tick):
                    currentAddInfo.tempo = tempoMsgInfo
            
            # ノートオン（ベロシティ0を除く）
            if ((msg.type == "note_on") and (msg.velocity != 0)):
                noteOnInfo[currentSectionIndex][i].append(
                    MidiMsgInfo(msg, globalTick, currentAddInfo)
                )
            # 音色
            elif (msg.type == "program_change"):
                currentAddInfo.program = MidiMsgInfo(msg, globalTick)
            # ピッチベンド
            elif (msg.type == "pitchwheel"):
                currentAddInfo.pitch = MidiMsgInfo(msg, globalTick)
            # パンポット
            elif (msg.is_cc(CONTROL_PANPOT)):
                currentAddInfo.pan = MidiMsgInfo(msg, globalTick)
            # メインボリューム
            elif (msg.is_cc(CONTROL_MAINVOLUME)):
                currentAddInfo.pan = MidiMsgInfo(msg, globalTick)
            # エクスプレッション
            elif (msg.is_cc(CONTROL_EXPRESSION)):
                currentAddInfo.pan = MidiMsgInfo(msg, globalTick)
            # RPN MSB
            elif (msg.is_cc(CONTROL_RPN_MSB)):
                tmpRPN[0] = msg.value
            # RPN LSB
            elif (msg.is_cc(CONTROL_RPN_LSB)):
                tmpRPN[1] = msg.value
            # RPN DATA MSB（ピッチベンドセンシティビティ）
            elif (msg.is_cc(CONTROL_RPN_DATA_MSB)):
                # どのRPNか特定できている
                if ((tmpRPN[0] >= 0) and (tmpRPN[1] >= 0)):
                    # ピッチベンドセンシティビティ
                    if ((tmpRPN[0] == 0) and (tmpRPN[1] == 0)):
                        currentAddInfo.pbsens = 2 #msg.value
                        if (msg.value != 2):
                            print(f"[Warning] Invalid pitch bend sensitivity: {msg.value}")
                    else:
                        print(f"[Warning] Unknown RPN: {tmpRPN[0]} {tmpRPN[1]}, Data msg: {msg}")
                else:
                    print(f"[Error] RPN Data without RPN specification: {tmpRPN[0]} {tmpRPN[1]}, Data msg: {msg}")
                    exit(1)
                # RPNの一時データリセット
                tmpRPN[0] = -1
                tmpRPN[1] = -1

    return noteOnInfo

# MIDIデータを受け取り、セクションごとに、トラック同士の類似度を求める
# 結果を辞書の配列に格納して返す
def CalcSimilarityBetweenTracksForEachSection(
        _midData: mido.MidiFile,
        _sectionStartBars,
        delay_max_tick: int,
        _ticksPerBar: int
):
    noteOnInfo = extractNoteOnInfo(_midData, _sectionStartBars, _ticksPerBar)
    resultDictList = []

    # セクションごとに
    for sectionIndex in range(len(_sectionStartBars) - 1):
        # セクションの情報を取得
        sectionEndTick = 0
        if (sectionIndex == len(_sectionStartBars) - 2): #最後のセクションなら
            sectionEndTick = _midData.totalTicks
        else:
            sectionEndTick = (_sectionStartBars[sectionIndex + 1] - 1)*_ticksPerBar
        sectionLengthTick = sectionEndTick - (_sectionStartBars[sectionIndex] - 1)*_ticksPerBar
        sectionLengthBar = sectionLengthTick / _ticksPerBar

        # 2-2. 総当たりで2つのトラックを比較
        # 先行トラック（trackX）
        for i, trackX in enumerate(noteOnInfo[sectionIndex][1:], start=1):
            # ノートオンが無いトラックは無視
            if (len(trackX) == 0):
                continue
            # 後続トラック（trackY）
            for j, trackY in enumerate(noteOnInfo[sectionIndex][1:], start=1):
                # ノートオンが無いトラックは無視
                if (len(trackY) == 0):
                    continue
                # 同じトラック同士は無視
                if (i == j):
                    continue

                # ディレイ関係を算出するための変数
                XBase_delayRelationScore = 0 # Xから見て、XからYにディレイ関係があるかを示すスコア
                YBase_delayRelationScore = 0 # Yから見て、XからYにディレイ関係があるかを示すスコア
                haveDelay = [] # トラックX内で、トラックYに後続する音が存在する音を記録する配列
                haveOriginal = [] # トラックY内で、トラックXに先行する音が存在する音を記録する配列
                netXNoteOnCount = getNetNoteCount(trackX) # トラックXの正味ノートオン数
                netYNoteOnCount = getNetNoteCount(trackY) # トラックYの正味ノートオン数

                # トラックX中の各ノートオンについて、
                # その直後に同じ音名の音がトラックYに現れるか（＝ディレイ音があるか）検証
                for noteOnX in trackX:
                    # 前から探索
                    for noteOnY in trackY:
                        # タイミングがディレイ範囲内か
                        if ((noteOnX.tick <= noteOnY.tick)
                            and (noteOnY.tick <= noteOnX.tick + delay_max_tick)):
                            # 音名が同じか
                            if (noteOnX.msg.note % 12 == noteOnY.msg.note % 12):
                                tmpNoteOn = copy.deepcopy(noteOnX)
                                tmpNoteOn.following = noteOnY
                                haveDelay.append(tmpNoteOn)

                # トラックY中の各ノートオンについて、
                # その直前に同じ音名の音がトラックXに現れるか（＝原音があるか）検証
                for noteOnY in trackY:
                    # 後ろから検索
                    for noteOnX in reversed(trackX):
                        # タイミングがディレイ範囲内か
                        if ((noteOnX.tick <= noteOnY.tick)
                            and (noteOnY.tick <= noteOnX.tick + delay_max_tick)):
                            # 音名が同じか
                            if (noteOnX.msg.note % 12 == noteOnY.msg.note % 12):
                                tmpNoteOn = copy.deepcopy(noteOnY)
                                tmpNoteOn.preceding = noteOnX
                                haveOriginal.append(tmpNoteOn)
                
                # スコア算出
                XBase_delayRelationScore = getNetNoteCount(haveDelay) / netXNoteOnCount
                YBase_delayRelationScore = getNetNoteCount(haveOriginal) / netYNoteOnCount

                # スコアが条件を満たす場合にのみ記録
                isStrong = (XBase_delayRelationScore >= DELAY_RELATION_SCORE_THRESHOLD)\
                            & (YBase_delayRelationScore >= DELAY_RELATION_SCORE_THRESHOLD)
                if (XBase_delayRelationScore >= DELAY_RELATION_SCORE_THRESHOLD):
                    # resultDictList.append(
                    #     analyzeAddData(haveDelay, XBase_delayRelationScore,\
                    #                    i, j, sectionIndex, sectionLengthBar,\
                    #                    _midData.ticks_per_beat, isStrong)
                    # )
                    for msgNum, msgInfo in enumerate(haveDelay):
                        resultDictList.append(
                            makeRecordFromMsgInfo(msgNum, msgInfo, XBase_delayRelationScore,\
                                            i, j, sectionIndex, sectionLengthBar,\
                                            _midData.ticks_per_beat, isStrong)
                        )
                if (YBase_delayRelationScore >= DELAY_RELATION_SCORE_THRESHOLD):
                    # resultDictList.append(
                    #     analyzeAddData(haveOriginal, YBase_delayRelationScore,\
                    #                    i, j, sectionIndex, sectionLengthBar,\
                    #                    _midData.ticks_per_beat, isStrong, False)
                    # )
                    for msgNum, msgInfo in enumerate(haveOriginal):
                        resultDictList.append(
                            makeRecordFromMsgInfo(msgNum, msgInfo, XBase_delayRelationScore,\
                                            i, j, sectionIndex, sectionLengthBar,\
                                            _midData.ticks_per_beat, isStrong, False)
                        )
    
    
    return resultDictList

# 追加情報の安全な取り出し
def _q(_instance: MidiMsgInfo, _member1: str, _member2: str, default):
    if (getattr(_instance.addInfo, _member1) is None):
        return default
    else:
        if (_member2 == ""):
            return getattr(_instance.addInfo, _member1)
        else:
            return getattr(getattr(_instance.addInfo, _member1).msg, _member2)

# 総合音量を算出
def getOverallVolume(_msg: MidiMsgInfo):
    return \
    _q(_msg, "mainVol", "value", MAINVOLUME_DEFAULT)\
    * _q(_msg, "express", "value", EXPRESSION_DEFAULT)\
    * _msg.msg.velocity\
    / (127 * 127 * 127)

# 2つの音色が同じグループにあるか調べる
def GetDiffProgramGroup(_program1: int, _program2: int):
    if (_program1 == _program2):
        return 0
    if ((_program1 // 8) == (_program2 // 8)):
        return 1
    return 2

# MidiMsgInfoから、レコードとなる辞書を作成する
def makeRecordFromMsgInfo(
        _msgInfoNum: int,
        _msgInfo: MidiMsgInfo, 
        _delayRelationScore: float, 
        _trackXNum: int, _trackYNum: int, 
        _sectionIndex: int, _sectionLengthBar, 
        _ticksPerBeat: int,
        _isStrong: bool,
        _isPre: bool =True
    ):
    # 必要な情報だけ抜き出して格納する
    infos = {
        # 共通データ
        "TicksPerBeat": _ticksPerBeat,
        "TrackX": _trackXNum,
        "TrackY": _trackYNum,
        "IsStrong": _isStrong,
        "Section": _sectionIndex,
        "SectionLength(Bar)": _sectionLengthBar,
        "Score": _delayRelationScore,
        "MsgNumber": _msgInfoNum,
        "GlobalTick": _msgInfo.tick,
        "NoteNumber": _msgInfo.msg.note % 12,
        # 個別データ
        "Base": "",
        "X_note": 0, #ノート番号
        "X_tempo": 0, #テンポ
        "X_program": 0, #音色
        "X_pitch": 0, #ピッチ
        "X_pan": 0, #パン
        "X_mainVol": 0, #主音量
        "X_expression": 0, #エクスプレッション
        "X_velocity": 0, #ベロシティ
        "X_ovVol": 0, #総合音量
        "Y_note": 0,
        "Y_tempo": 0,
        "Y_program": 0,
        "Y_pitch": 0,
        "Y_pan": 0,
        "Y_mainVol": 0,
        "Y_expression": 0,
        "Y_velocity": 0,
        "Y_ovVol": 0,
        # 差分
        "Diff_timing": 0, #発音タイミングの差
        "Diff_timing(MicroSeconds)": 0, #発音タイミングの差（実時間）
        "Diff_program": 0, #音色の差
        "Diff_program(group)": 0, #音色グループの差
        "Diff_pitch": 0, #ピッチの差
        "Diff_pan": 0, #パンの差
        "Diff_mainVol": 0, #主音量の差
        "Diff_expression": 0, #エクスプレッションの差
        "Diff_velocity": 0, #ベロシティの差
        "Diff_ovVol": 0, #総合音量の差
        "Diff_octave": 0 #オクターブの差
    }

    if (_isPre):
        infos["Base"] = "X"
        infos["X_note"] = _msgInfo.msg.note
        infos["X_tempo"] = _q(_msgInfo, "tempo", "tempo", PROGRAM_DEFAULT)
        infos["X_program"] = _q(_msgInfo, "program", "program", PROGRAM_DEFAULT)
        infos["X_pitch"] =\
            _q(_msgInfo, "pitch", "pitch", PITCH_DEFAULT)\
            * _q(_msgInfo, "pbsens", "", PBSENS_DEFAULT)
        infos["X_pan"] = _q(_msgInfo, "pan", "value", PAN_DEFAULT)
        infos["X_mainVol"] = _q(_msgInfo, "mainVol", "value", MAINVOLUME_DEFAULT)
        infos["X_expression"] = _q(_msgInfo, "express", "value", EXPRESSION_DEFAULT)
        infos["X_velocity"] = _msgInfo.msg.velocity
        infos["X_ovVol"] = getOverallVolume(_msgInfo)
        
        infos["Y_note"] = _msgInfo.following.msg.note
        infos["Y_tempo"] = _q(_msgInfo.following, "tempo", "tempo", TEMPO_DEFAULT)
        infos["Y_program"] = _q(_msgInfo.following, "program", "program", PROGRAM_DEFAULT)
        infos["Y_pitch"] =\
            _q(_msgInfo.following, "pitch", "pitch", PITCH_DEFAULT)\
            * _q(_msgInfo.following, "pbsens", "", PBSENS_DEFAULT)
        infos["Y_pan"] = _q(_msgInfo.following, "pan", "value", PAN_DEFAULT)
        infos["Y_mainVol"] = _q(_msgInfo.following, "mainVol", "value", MAINVOLUME_DEFAULT)
        infos["Y_expression"] = _q(_msgInfo.following, "express", "value", EXPRESSION_DEFAULT)
        infos["Y_velocity"] = _msgInfo.following.msg.velocity
        infos["Y_ovVol"] = getOverallVolume(_msgInfo.following)
        
        infos["Diff_timing"] = _msgInfo.following.tick - _msgInfo.tick
        infos["Diff_timing(MicroSeconds)"] =\
            infos["Diff_timing"] * infos["X_tempo"] / infos["TicksPerBeat"]
        infos["Diff_program"] = infos["Y_program"] - infos["X_program"]
        infos["Diff_program(group)"] = GetDiffProgramGroup(infos["X_program"], infos["Y_program"])
        infos["Diff_pitch"] = infos["Y_pitch"] - infos["X_pitch"]
        infos["Diff_pan"] = infos["Y_pan"] - infos["X_pan"]
        infos["Diff_mainVol"] = infos["Y_mainVol"] - infos["X_mainVol"]
        infos["Diff_expression"] = infos["Y_expression"] - infos["X_expression"]
        infos["Diff_velocity"] = infos["Y_velocity"] - infos["X_velocity"]
        infos["Diff_ovVol"] = infos["Y_ovVol"] - infos["X_ovVol"]
        infos["Diff_octave"] = (_msgInfo.following.msg.note - _msgInfo.msg.note) / 12
    else:
        infos["Base"] = "Y"
        infos["Y_note"] = _msgInfo.msg.note
        infos["Y_tempo"] = _q(_msgInfo, "tempo", "tempo", PROGRAM_DEFAULT)
        infos["Y_program"] = _q(_msgInfo, "program", "program", PROGRAM_DEFAULT)
        infos["Y_pitch"] =\
            _q(_msgInfo, "pitch", "pitch", PITCH_DEFAULT)\
            * _q(_msgInfo, "pbsens", "", PBSENS_DEFAULT)
        infos["Y_pan"] = _q(_msgInfo, "pan", "value", PAN_DEFAULT)
        infos["Y_mainVol"] = _q(_msgInfo, "mainVol", "value", MAINVOLUME_DEFAULT)
        infos["Y_expression"] = _q(_msgInfo, "express", "value", EXPRESSION_DEFAULT)
        infos["Y_velocity"] = _msgInfo.msg.velocity
        infos["Y_ovVol"] = getOverallVolume(_msgInfo)

        infos["X_note"] = _msgInfo.preceding.msg.note
        infos["X_tempo"] = _q(_msgInfo.preceding, "tempo", "tempo", TEMPO_DEFAULT)
        infos["X_program"] = _q(_msgInfo.preceding, "program", "program", PROGRAM_DEFAULT)
        infos["X_pitch"] =\
            _q(_msgInfo.preceding, "pitch", "pitch", PITCH_DEFAULT)\
            * _q(_msgInfo.preceding, "pbsens", "", PBSENS_DEFAULT)
        infos["X_pan"] = _q(_msgInfo.preceding, "pan", "value", PAN_DEFAULT)
        infos["X_mainVol"] = _q(_msgInfo.preceding, "mainVol", "value", MAINVOLUME_DEFAULT)
        infos["X_expression"] = _q(_msgInfo.preceding, "express", "value", EXPRESSION_DEFAULT)
        infos["X_velocity"] = _msgInfo.preceding.msg.velocity
        infos["X_ovVol"] = getOverallVolume(_msgInfo.preceding)
        
        infos["Diff_timing"] = _msgInfo.tick - _msgInfo.preceding.tick
        infos["Diff_timing(MicroSeconds)"] =\
            infos["Diff_timing"] * infos["X_tempo"] / infos["TicksPerBeat"]
        infos["Diff_program"] = infos["Y_program"] - infos["X_program"]
        infos["Diff_program(group)"] = GetDiffProgramGroup(infos["Y_program"], infos["X_program"])
        infos["Diff_pitch"] = infos["Y_pitch"] - infos["X_pitch"]
        infos["Diff_pan"] = infos["Y_pan"] - infos["X_pan"]
        infos["Diff_mainVol"] = infos["Y_mainVol"] - infos["X_mainVol"]
        infos["Diff_expression"] = infos["Y_expression"] - infos["X_expression"]
        infos["Diff_velocity"] = infos["Y_velocity"] - infos["X_velocity"]
        infos["Diff_ovVol"] = infos["Y_ovVol"] - infos["X_ovVol"]
        infos["Diff_octave"] = (_msgInfo.msg.note - _msgInfo.preceding.msg.note) / 12

    return infos


#================
# 分析関数（全体）
#================
# 号数、ファイル名、変換されたものかどうか、という情報からアクセスに必要な相対パスを求める
def getMidifilePath(_issueNum: int, _filename: str, _converted: bool =True):
    relativePath = f"../data/{_issueNum}/"
    if _converted:
        relativePath += "conv/"
    relativePath += _filename

    return relativePath

# 指定されたファイルを分析する
def analyzeSingleMidifile(_issueNum: int, _filename: str, _converted: bool =True):
    # ================
    # データ読み込み
    # ================
    # SMF単体読み込み
    midData = mido.MidiFile(getMidifilePath(_issueNum, _filename, _converted))
    # 曲名表示
    print(f"File: {midData.filename}, Sequence Name: {getSequenceName(midData)}")
    # フォーマット1なら、いったん0に変換
    if (midData.type == 1):
        midData = SMF1to0(midData)
    # フォーマット1に変換、総Tick数を取得
    midData = SMF0to1AndGetTotalTicks(midData)

    # ================
    # 分析
    # ================
    # 1. プログラムチェンジでセクションを区切る
    # メタメッセージから拍子を取得
    (timeSigNume, timeSigDeno) = getTimeSignature(midData)
    #print(f"- Time Signature: {timeSigNume} / {timeSigDeno}")
    # 1小節が何Tickか求める
    ticksPerBar = midData.ticks_per_beat * (4/timeSigDeno) * timeSigNume
    # 定数をもとに、分析に必要な具体的な値を求める
    delay_max_tick = midData.ticks_per_beat * DELAY_MAX_BEAT
    # セクション開始小節を格納する配列
    # 配列の内の数字nは、n小節目の始まりを意味する（n=1~）
    # 便宜上、末尾にintの最大値を追加
    sectionStartBars = getSectionStartBars(midData, ticksPerBar)
    #print(f"Sections: {sectionStartBars}")

    # 2. セクションごとに、トラック同士の類似度を求める。
    return CalcSimilarityBetweenTracksForEachSection(midData, sectionStartBars, delay_max_tick, ticksPerBar)

# 調査対象のファイルをすべて分析する
def analyzeAllMidifiles(_isDebug: bool =False):
    # 調査結果を格納する辞書
    survayResult = {}
    # 調査したファイルを格納するリストと、ファイルのハッシュを格納するリスト
    fileList = []
    fileHashList = []

    # SMF走査
    for issueNum in range(ISSUE_MIN, ISSUE_MAX+1):
        # 変換されていないSMF
        dirPath = getMidifilePath(issueNum, "", False)
        print(dirPath)
        for filename in os.listdir(dirPath):
            filePath = os.path.join(dirPath, filename)
            if (os.path.isfile(filePath)
                and os.path.splitext(filename)[1].lower() == ".mid"):
                # 重複ファイルを検索
                fileHash = ""
                with open(filePath, mode="rb") as f:
                    fileHash = sha256(f.read()).hexdigest()
                if (fileHash in fileHashList):
                    print(f"[Info] Same file exists: {filename} = {fileList[fileHashList.index(fileHash)]}")
                    continue
                # 初出ファイルなら、リストに追加し、分析
                else:
                    fileList.append(filePath)
                    fileHashList.append(fileHash)
                    survayResult[filePath] = analyzeSingleMidifile(issueNum, filename, False)
        # 変換されたSMF
        dirPath = getMidifilePath(issueNum, "", True)
        for filename in os.listdir(dirPath):
            filePath = os.path.join(dirPath, filename)
            if (os.path.isfile(filePath)
                and os.path.splitext(filename)[1].lower() == ".mid"):
                # 重複ファイルを検索
                fileHash = ""
                with open(filePath, mode="rb") as f:
                    fileHash = sha256(f.read()).hexdigest()
                if (fileHash in fileHashList):
                    print(f"[Info] Same file exists: {filename} = {fileList[fileHashList.index(fileHash)]}")
                    continue
                # 初出ファイルなら、リストに追加し、分析
                else:
                    fileList.append(filePath)
                    fileHashList.append(fileHash)
                    survayResult[filePath] = analyzeSingleMidifile(issueNum, filename, True)
        if (_isDebug):
            break
    return survayResult

# 調査結果を書き出す
def outputResult(result, csvFilename: str):
    # 区切り文字
    sep = ";"
    # 列名
    outputText = "File"
    for filePath in result.keys():
        for record in result[filePath]:
            for recordKey in record.keys():
                outputText += f"{sep}{recordKey}"
            break
        break
    outputText += "\n"
    
    # 実データ
    for filePath in result.keys():
        for record in result[filePath]:
            outputText += filePath
            for recordKey in record.keys():
                outputText += f"{sep}{record[recordKey]}"
            outputText += "\n"
    
    with open(csvFilename, mode="w") as f:
        f.write(outputText)


# ================
# メイン処理
# ================
# 調査結果を格納する辞書作成
result = analyzeAllMidifiles(False)

# 調査結果を書き出し
outputResult(result, "out.csv")
