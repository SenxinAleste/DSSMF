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
    # �f�[�^�ǂݍ���
    # ================
    # SMF�P�̓ǂݍ���
    midData = mido.MidiFile(getMidifilePath(_issueNum, _filename, _converted))
    
    # ���b�Z�[�W��ޒ���
    for track in midData.tracks:
        for msg in track:
            keyStr = f"{msg.type}"
            if (msg.is_cc()):
                keyStr = f"cc_{msg.control:0=4}"
            incrementDict(_resDict, keyStr)    


# �����Ώۂ̃t�@�C�������ׂĕ��͂���
def analyzeAllMidifiles(_isDebug: bool =False):
    # �������ʂ��i�[���鎫��
    survayResult = {}
    # ���������t�@�C�����i�[���郊�X�g�ƁA�t�@�C���̃n�b�V�����i�[���郊�X�g
    fileList = []
    fileHashList = []

    # SMF����
    for issueNum in range(ISSUE_MIN, ISSUE_MAX+1):
        # �ϊ�����Ă��Ȃ�SMF
        dirPath = getMidifilePath(issueNum, "", False)
        print(dirPath)
        for filename in os.listdir(dirPath):
            filePath = os.path.join(dirPath, filename)
            if (os.path.isfile(filePath)
                and os.path.splitext(filename)[1].lower() == ".mid"):
                # �d���t�@�C��������
                fileHash = ""
                with open(filePath, mode="rb") as f:
                    fileHash = sha256(f.read()).hexdigest()
                if (fileHash in fileHashList):
                    continue
                # ���o�t�@�C���Ȃ�A���X�g�ɒǉ����A����
                else:
                    fileList.append(filePath)
                    fileHashList.append(fileHash)
                    analyzeSingleMidifile(survayResult, issueNum, filename, False)
        # �ϊ����ꂽSMF
        dirPath = getMidifilePath(issueNum, "", True)
        for filename in os.listdir(dirPath):
            filePath = os.path.join(dirPath, filename)
            if (os.path.isfile(filePath)
                and os.path.splitext(filename)[1].lower() == ".mid"):
                # �d���t�@�C��������
                fileHash = ""
                with open(filePath, mode="rb") as f:
                    fileHash = sha256(f.read()).hexdigest()
                if (fileHash in fileHashList):
                    continue
                # ���o�t�@�C���Ȃ�A���X�g�ɒǉ����A����
                else:
                    fileList.append(filePath)
                    fileHashList.append(fileHash)
                    analyzeSingleMidifile(survayResult, issueNum, filename, True)
        if (_isDebug):
            break
    
    return survayResult


d = analyzeAllMidifiles()
print(sorted(d.items()))
