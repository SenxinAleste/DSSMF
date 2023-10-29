#!python3.10
# coding: shift_jis

import mido
import os
from hashlib import sha256


ISSUE_MIN = 12
ISSUE_MAX = 27

# SMFフォーマット1を0に変換する関数
def SMF1to0(_midOrg: mido.MidiFile):
    # フォーマット確認
    if (_midOrg.type != 1):
        return _midOrg

    # 変換
    midCnv = mido.MidiFile(type=0)
    midCnv.add_track()
    midCnv.tracks[0] = mido.merge_tracks(_midOrg.tracks)

    return midCnv

def getMidifilePath(_issueNum: int, _filename: str, _converted: bool =True):
    relativePath = f"../data/{_issueNum}/"
    if _converted:
        relativePath += "conv/"
    relativePath += _filename

    return relativePath

def analyzeSingleMidifile(_resDict: dict, _issueNum: int, _filename: str, _converted: bool =True):
    # ================
    # データ読み込み
    # ================
    # SMF単体読み込み
    midFilePath = getMidifilePath(_issueNum, _filename, _converted)
    midData = mido.MidiFile(midFilePath)
    midCnv = SMF1to0(midData)
    
    # メッセージ種類調査
    currentOnVoice = 0
    maxOnVoice = 0
    maxOnVoiceTick = 0
    globalTick = 0
    decReserve = 0
    for msg in midCnv.tracks[0]:
        globalTick += msg.time
        if (msg.time > 0):
            currentOnVoice -= decReserve
            decReserve = 0
            if (currentOnVoice > maxOnVoice):
                maxOnVoice = currentOnVoice
                maxOnVoiceTick = globalTick
        if ((msg.type == "note_on") and (msg.velocity != 0)):
            currentOnVoice += 1
            # ドラム音
            if (msg.channel == 9):
                decReserve += 1
        elif ((msg.type == "note_off")
              or
              ((msg.type == "note_on") and (msg.velocity == 0))):
            currentOnVoice -= 1
            # ドラム音
            if (msg.channel == 9):
                decReserve -= 1
    
    _resDict[f"{midFilePath}___{maxOnVoiceTick}"] = maxOnVoice


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
                    continue
                # 初出ファイルなら、リストに追加し、分析
                else:
                    fileList.append(filePath)
                    fileHashList.append(fileHash)
                    analyzeSingleMidifile(survayResult, issueNum, filename, False)
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
                    continue
                # 初出ファイルなら、リストに追加し、分析
                else:
                    fileList.append(filePath)
                    fileHashList.append(fileHash)
                    analyzeSingleMidifile(survayResult, issueNum, filename, True)
        if (_isDebug):
            break
    
    return survayResult


d = analyzeAllMidifiles()

d_sorted = sorted(d.items(), key = lambda kv : kv[1])

print(d_sorted)

underLimitation = 0
aroundLimitation = 0
overLimitation = 0
for v in d.values():
    if (v <= 18):
        underLimitation += 1
    elif (v <= 20):
        aroundLimitation += 1
    else:
        overLimitation += 1

print(f"~18: {underLimitation}, 19~20: {aroundLimitation}, 21~: {overLimitation}")