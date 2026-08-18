from minidora_k3.演算 import (
    solve_arithmetic,
    solve_boolean,
    solve_count,
    solve_date,
    solve_ordering,
    solve_swaps,
)


def test_数量分類集計():
    result = solve_count(
        "私はリンゴ2個、バナナ3本、椅子1脚を持っています。全部で果物は何個ありますか？",
        {"果物": ["リンゴ", "バナナ"]},
    )
    assert result.answer == "5"


def test_数量全対象集計():
    result = solve_count("私は椅子1脚、机2台、ランプ3台を持っています。全部で物品はいくつありますか？", {"物品": ["*"]})
    assert result.answer == "6"


def test_交換状態遷移():
    text = """アリス、ボブ、クレアの3人はゲームをしています。ゲーム開始時、各プレイヤーはそれぞれ1個のボールを持っています：アリスは青色のボール、ボブは赤色のボール、クレアは黄色のボールです。
ゲームが進むにつれて、プレイヤーたちはペアを組んでボールを交換します。まずクレアとボブがボールを交換します。次にクレアとアリスがボールを交換します。最後にボブとクレアがボールを交換します。ゲーム終了時、アリスが持っているボールは
選択肢:
(A) 青色のボール
(B) 赤色のボール
(C) 黄色のボール"""
    assert solve_swaps(text).answer == "(B)"


def test_順序制約():
    text = """以下の各段落では、固定された順序で配置された3つの物体のセットについて説明しています。棚には3冊の本があります――青い本、オレンジ色の本、赤い本です。青い本は最も右側に位置しています。オレンジ色の本は最も左側に位置しています。
選択肢:
(A) 青い本は左から2冊目である
(B) オレンジ色の本は左から2冊目である
(C) 赤い本は左から2冊目である"""
    assert solve_ordering(text).answer == "(C)"


def test_日付計算():
    text = """今日は2020年のクリスマス・イブです。明日の日付はMM/DD/YYYYで何ですか？
選択肢:
(A) 12/23/2020
(B) 12/25/2020
(C) 01/01/2021"""
    assert solve_date(text).answer == "(B)"


def test_論理優先順位():
    assert solve_boolean("not True or False は").answer == "False"


def test_算術優先順位():
    assert solve_arithmetic("(2 + 3) * 4 =").answer == "20"
