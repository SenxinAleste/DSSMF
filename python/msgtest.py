#!python3.10
# coding: shift_jis

import mido
import os
from hashlib import sha256


ISSUE_MIN = 12
ISSUE_MAX = 27

def getMidifilePath(_issueNum: int, _filename: str, _converted: bool =True):
    relativePath = f"../data/{_issueNum}/"
    if _converted:
        relativePath += "conv/"
    relativePath += _filename

    return relativePath

def incrementDict(_d: dict, _key:str):
    if (_key not in _d):
        _d[_key] = 1
    else:
        _d[_key] += 1

def analyzeSingleMidifile(_resDict: dict, _issueNum: int, _filename: str, _converted: bool =True):
    # ================
    # データ読み込み
    # ================
    # SMF単体読み込み
    midData = mido.MidiFile(getMidifilePath(_issueNum, _filename, _converted))
    
    # メッセージ種類調査
    for track in midData.tracks:
        for msg in track:
            keyStr = f"{msg.type}"
            if (msg.is_cc()):
                keyStr = f"cc_{msg.control:0=4}"
            incrementDict(_resDict, keyStr)    


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
print(sorted(d.items()))
