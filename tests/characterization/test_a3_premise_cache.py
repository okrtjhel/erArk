# -*- coding: UTF-8 -*-
"""
L2/L3 特性测试：Round A3 前提系统单趟结果缓存验证。

验证目标：
  1. get_weight_from_premise_dict 内部的 now_premise_data 缓存在单趟内生效：
     同一前提在同一趟 calculated_premise_dict 中只被求值一次。
  2. search_target 的 premise_data 跨多次调用共用：
     同一前提在一次 find_character_target 过程中只被求值一次。
  3. 缓存不洩漏：两个独立的 calculated_premise_dict / premise_data 之间完全隔离，
     第一趟改变状态后，第二趟必须反映新状态。
  4. 全 NPC 遍历型前提（player_have_other_lover / player_have_other_pet 系列）
     在同一趟内结果一致，且不同 character_id 呼叫不共用缓存（character_id 相关）。
  5. handle_have_moved 有副作用，不可安全缓存跨调用（文档测试）。

安全原则：测试只读/构造最小 cache，不写入真实存档，不启动 GUI。
"""
import sys
import os
import datetime
import pytest
from unittest.mock import patch

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ── fixture：最小 cache 环境 ───────────────────────────────────────────────────

@pytest.fixture(scope="module")
def loaded_modules(game_config_loaded):
    """
    输入：game_config_loaded fixture（已由 conftest 提供）
    回傳：dict，含已导入的核心模块
    功能：确保 handle_premise 等核心模块在 module 范围内只导入一次。
    """
    from Script.Core import cache_control, game_type, constant
    from Script.Design import handle_premise
    import Script.Design.handle_premise.handle_premise_fall as hp_fall
    import Script.Design.handle_premise.handle_premise_other as hp_other
    return {
        "cache_control": cache_control,
        "game_type": game_type,
        "constant": constant,
        "handle_premise": handle_premise,
        "hp_fall": hp_fall,
        "hp_other": hp_other,
    }


def _inject_cache_to_all_premise_modules(cache_obj, loaded_modules):
    """
    输入：cache 实例、loaded_modules dict
    回傳：无
    功能：将 cache 实例注入到所有已导入的前提模块的模块级 cache 变量，
          以及 cache_control.cache，使前提函数能找到正确的 cache。
    """
    import Script.Design.handle_premise.handle_premise_fall as hp_fall
    import Script.Design.handle_premise.handle_premise_other as hp_other
    import Script.Design.handle_premise.handle_premise_sp_flag as hp_spflag
    import Script.Design.handle_premise.handle_premise_base_value as hp_bv
    import Script.Design.handle_premise.handle_premise_talent as hp_talent
    import Script.Design.handle_premise.handle_premise_ability as hp_ability
    import Script.Design.handle_premise.handle_premise_H as hp_h
    import Script.Design.handle_premise.handle_premise_time as hp_time
    import Script.Design.handle_premise.handle_premise_dirty as hp_dirty
    import Script.Design.handle_premise.handle_premise_cloth as hp_cloth
    import Script.Design.handle_premise.handle_premise_place as hp_place
    import Script.Design.handle_premise.handle_premise_entertainment as hp_enter
    import Script.Design.handle_premise.handle_premise_arts as hp_arts
    import Script.Design.handle_premise.handle_premise_first as hp_first
    import Script.Design.handle_premise.handle_premise_last_cmd as hp_last
    import Script.Design.handle_premise.handle_premise_assistant as hp_asst
    import Script.Design.handle_premise.handle_premise_work as hp_work

    mods = [hp_fall, hp_other, hp_spflag, hp_bv, hp_talent, hp_ability,
            hp_h, hp_time, hp_dirty, hp_cloth, hp_place, hp_enter,
            hp_arts, hp_first, hp_last, hp_asst, hp_work]
    for mod in mods:
        mod.cache = cache_obj

    # 也更新 __init__.py 的 cache
    loaded_modules["handle_premise"].cache = cache_obj
    # 更新 cache_control
    loaded_modules["cache_control"].cache = cache_obj


def _make_npc(game_type_module, char_id: int, talent_dict: dict = None, game_config_mod=None) -> object:
    """
    输入：game_type 模块、角色 id、素质字典（可选）、game_config 模块（可选）
    回傳：Character 实例
    功能：快速构造最小 NPC 角色数据。
          如果传入 game_config_mod，则正确初始化 body_item（避免 KeyError）。
    """
    npc = game_type_module.Character()
    npc.cid = char_id
    npc.target_character_id = char_id
    npc.talent = {i: 0 for i in range(300)}
    if talent_dict:
        npc.talent.update(talent_dict)
    npc.favorability = {0: 0}
    npc.behavior.start_time = datetime.datetime(2, 1, 1, 8, 0)
    # 初始化 body_item，避免 handle_self_now_gag 等前提发生 KeyError
    if game_config_mod is not None:
        for i in game_config_mod.config_body_item:
            item_data = game_config_mod.config_body_item[i]
            item_id = item_data.item_id
            item_name = game_config_mod.config_item[item_id].name
            npc.h_state.body_item[i] = [item_name, False, None]
    return npc


@pytest.fixture
def fresh_cache(loaded_modules, game_config_loaded):
    """
    输入：loaded_modules、game_config_loaded
    回傳：初始化好的最小 Cache 实例（每个测试独立一份）
    功能：构造最小 cache，设定玩家角色（id=0），并将 cache 注入所有前提模块。
    """
    game_type = loaded_modules["game_type"]

    cache = game_type.Cache()
    _inject_cache_to_all_premise_modules(cache, loaded_modules)

    # 玩家（传入 game_config_loaded 以正确初始化 body_item）
    pl = _make_npc(game_type, 0, game_config_mod=game_config_loaded)
    pl.target_character_id = 0
    cache.character_data[0] = pl
    cache.npc_id_got = {0}

    # 保存 game_config 引用供测试使用
    cache._test_game_config = game_config_loaded

    return cache


# ── 测试 1：get_weight_from_premise_dict 内置缓存正确性 ──────────────────────

class TestGetWeightFromPremiseDictCaching:
    """验证 get_weight_from_premise_dict 使用 calculated_premise_dict 的缓存行为。"""

    def test_same_premise_cached_within_one_pass(self, loaded_modules, fresh_cache):
        """
        输入：同一前提集合，连续两次调用 get_weight_from_premise_dict，传入同一 calculated_premise_dict
        回傳：无
        功能：确认第二次调用直接使用缓存结果，两次返回的权重完全相同，
              且实际前提处理器只被调用一次。
        """
        handle_premise = loaded_modules["handle_premise"]
        constant = loaded_modules["constant"]

        call_count = {"n": 0}
        fake_premise_id = "__test_single_call__"

        def counting_handler(cid):
            call_count["n"] += 1
            return 1

        constant.handle_premise_data[fake_premise_id] = counting_handler

        try:
            premise_set = frozenset({fake_premise_id})
            calculated_premise_dict = {}

            # 第一次调用
            w1, calculated_premise_dict = handle_premise.get_weight_from_premise_dict(
                premise_set, 0, calculated_premise_dict
            )
            # 第二次调用（传入已有缓存的 dict）
            w2, calculated_premise_dict = handle_premise.get_weight_from_premise_dict(
                premise_set, 0, calculated_premise_dict
            )

            assert w1 == w2, f"两次调用权重应相同: {w1} != {w2}"
            assert call_count["n"] == 1, (
                f"同一前提在缓存复用时应只被实际评估一次，但被调用了 {call_count['n']} 次"
            )
        finally:
            del constant.handle_premise_data[fake_premise_id]

    def test_weight_with_cache_equals_weight_without_cache(self, loaded_modules, fresh_cache):
        """
        输入：简单前提集合，分别用空 calculated_premise_dict 和预填缓存调用
        回傳：无
        功能：确认「有缓存」和「无缓存」两条路径对相同状态给出相同权重，证明等价性。
        """
        handle_premise = loaded_modules["handle_premise"]
        constant = loaded_modules["constant"]

        fake_premise_id = "__test_equiv__"
        constant.handle_premise_data[fake_premise_id] = lambda cid: 1

        try:
            premise_set = frozenset({fake_premise_id})

            # 路径 A：空缓存（从头计算）
            w_fresh, _ = handle_premise.get_weight_from_premise_dict(
                premise_set, 0, {}
            )

            # 路径 B：预填缓存（直接走缓存路径）
            pre_cached = {fake_premise_id: w_fresh}
            w_cached, _ = handle_premise.get_weight_from_premise_dict(
                premise_set, 0, dict(pre_cached)
            )

            assert w_fresh == w_cached, (
                f"有缓存与无缓存结果不一致: fresh={w_fresh}, cached={w_cached}"
            )
        finally:
            del constant.handle_premise_data[fake_premise_id]

    def test_zero_weight_premise_recorded_in_cache(self, loaded_modules, fresh_cache):
        """
        输入：包含一个永远返回 0 的假前提的集合
        回傳：无
        功能：确认不满足的前提（权重 0）也被记录进 calculated_premise_dict（缓存了失败结果），
              确保下次不会重新评估。
        """
        handle_premise = loaded_modules["handle_premise"]
        constant = loaded_modules["constant"]

        fake_premise_id = "__test_zero_premise__"
        constant.handle_premise_data[fake_premise_id] = lambda cid: 0

        try:
            premise_set = frozenset({fake_premise_id})
            calculated_premise_dict = {}

            w, updated_dict = handle_premise.get_weight_from_premise_dict(
                premise_set, 0, calculated_premise_dict
            )

            assert w == 0, f"不满足前提时总权重应为 0，实际: {w}"
            assert fake_premise_id in updated_dict, "不满足的前提也应被记录入缓存"
            assert updated_dict[fake_premise_id] == 0, "缓存中该前提的值应为 0"
        finally:
            del constant.handle_premise_data[fake_premise_id]

    def test_multiple_premises_all_cached(self, loaded_modules, fresh_cache):
        """
        输入：包含多个假前提的集合，每个都应被缓存
        回傳：无
        功能：确认多前提集合中所有满足的前提都被记录进缓存字典。
        """
        handle_premise = loaded_modules["handle_premise"]
        constant = loaded_modules["constant"]

        premises = {
            "__test_multi_a__": 2,
            "__test_multi_b__": 3,
        }
        for pid, weight in premises.items():
            constant.handle_premise_data[pid] = (lambda w: lambda cid: w)(weight)

        try:
            premise_set = frozenset(premises.keys())
            calc_dict = {}
            w, calc_dict = handle_premise.get_weight_from_premise_dict(
                premise_set, 0, calc_dict
            )

            assert w == 5, f"权重应为 2+3=5，实际: {w}"
            for pid in premises:
                assert pid in calc_dict, f"前提 {pid} 应在缓存中"
        finally:
            for pid in premises:
                del constant.handle_premise_data[pid]


# ── 测试 2：缓存不洩漏（两趟完全隔离） ────────────────────────────────────────

class TestNoCacheLeak:
    """验证两次独立调用之间缓存不洩漏。"""

    def test_fresh_dict_triggers_new_evaluation(self, loaded_modules, fresh_cache):
        """
        输入：两次调用各自使用独立的 calculated_premise_dict
        回傳：无
        功能：确认两趟各自独立评估，计数器被调用两次（而非一次命中缓存）。
        """
        handle_premise = loaded_modules["handle_premise"]
        constant = loaded_modules["constant"]

        call_count = {"n": 0}
        fake_premise_id = "__test_fresh_eval__"
        constant.handle_premise_data[fake_premise_id] = lambda cid: (call_count.update({"n": call_count["n"] + 1}) or 1)

        try:
            premise_set = frozenset({fake_premise_id})

            # 趟次 1：独立缓存
            w1, _ = handle_premise.get_weight_from_premise_dict(premise_set, 0, {})
            count_1 = call_count["n"]

            # 趟次 2：独立缓存（不传入前一趟的结果）
            w2, _ = handle_premise.get_weight_from_premise_dict(premise_set, 0, {})
            count_2 = call_count["n"]

            assert w1 == 1 and w2 == 1
            assert count_1 == 1, f"第一趟应调用一次，实际: {count_1}"
            assert count_2 == 2, f"第二趟（新缓存）也应调用一次，累计: {count_2}"
        finally:
            del constant.handle_premise_data[fake_premise_id]

    def test_state_change_between_passes_reflected(self, loaded_modules, fresh_cache):
        """
        输入：同一前提集合，在状态改变前后各用独立缓存调用一次
        回傳：无
        功能：证明两次独立趟次之间，前一趟的缓存不会影响后一趟——
              状态改变后，新的独立调用能正确反映新状态（缓存无洩漏）。
        """
        handle_premise = loaded_modules["handle_premise"]
        constant = loaded_modules["constant"]

        state_flag = {"value": 0}
        fake_premise_id = "__test_state_change__"
        constant.handle_premise_data[fake_premise_id] = lambda cid: state_flag["value"]

        try:
            premise_set = frozenset({fake_premise_id})

            # 趟次 1：状态为 0
            state_flag["value"] = 0
            w_before, _ = handle_premise.get_weight_from_premise_dict(
                premise_set, 0, {}  # 独立缓存
            )
            assert w_before == 0, f"状态 0 时权重应为 0，实际: {w_before}"

            # 改变状态
            state_flag["value"] = 1

            # 趟次 2：全新缓存，应反映新状态
            w_after, _ = handle_premise.get_weight_from_premise_dict(
                premise_set, 0, {}  # 独立缓存
            )
            assert w_after == 1, f"状态改为 1 后（新缓存），权重应为 1，实际: {w_after}"
        finally:
            del constant.handle_premise_data[fake_premise_id]

    def test_reusing_old_cache_causes_stale_result(self, loaded_modules, fresh_cache):
        """
        输入：将第一趟的 calculated_premise_dict 传入第二趟（错误做法）
        回傳：无
        功能：文档测试——证明跨趟复用缓存字典会导致脏数据，确认不应该这样做。
        """
        handle_premise = loaded_modules["handle_premise"]
        constant = loaded_modules["constant"]

        state_flag = {"value": 0}
        fake_premise_id = "__test_stale_cache__"
        constant.handle_premise_data[fake_premise_id] = lambda cid: state_flag["value"]

        try:
            premise_set = frozenset({fake_premise_id})

            # 趟次 1：状态为 0，缓存了 0
            state_flag["value"] = 0
            w1, shared_dict = handle_premise.get_weight_from_premise_dict(
                premise_set, 0, {}
            )
            assert w1 == 0
            assert shared_dict.get(fake_premise_id) == 0

            # 改变状态为 1
            state_flag["value"] = 1

            # 趟次 2：「错误地」复用旧缓存 → 得到旧值（证明跨趟复用危险性）
            w2, _ = handle_premise.get_weight_from_premise_dict(
                premise_set, 0, shared_dict  # 错误的跨趟复用
            )
            # 由于缓存中已有值 0，且 0 时直接短路 break，结果依然为 0（脏缓存污染）
            assert w2 == 0, (
                "复用旧缓存时即使状态变 1，仍错误返回 0——证明跨趟复用的危险性"
            )
        finally:
            del constant.handle_premise_data[fake_premise_id]


# ── 测试 3：全 NPC 遍历型前提正确性与 character_id 相关性 ─────────────────────

class TestNpcTraversalPremises:
    """
    验证 handle_player_have_other_lover / handle_player_have_other_pet 系列
    的遍历正确性及 character_id 相关性。
    """

    def _setup_npcs(self, fresh_cache, game_type_module, npc_ids, lover_npc_id=None):
        """
        输入：cache 实例、game_type 模块、NPC id 列表、可选的恋人 NPC id
        回傳：无
        功能：在 cache 中注册多个 NPC，如果指定 lover_npc_id，
              该 NPC 会被设置爱情陷落3级素质（talent 201 + 203）。
        """
        gc = getattr(fresh_cache, "_test_game_config", None)
        for cid in npc_ids:
            npc = _make_npc(game_type_module, cid, game_config_mod=gc)
            if cid == lover_npc_id:
                # 爱情系陷落 1 级（201）且 3 级（203）
                npc.talent[201] = 1
                npc.talent[203] = 1
            fresh_cache.character_data[cid] = npc
            fresh_cache.npc_id_got.add(cid)

    def test_player_have_other_lover_detects_lover(self, loaded_modules, fresh_cache):
        """
        输入：cache 中有一个具备爱情陷落3级素质的 NPC（NPC 2）
        回傳：无
        功能：验证 handle_player_have_other_lover 正确识别出存在其他恋人。
        """
        from Script.Design.handle_premise.handle_premise_fall import (
            handle_player_have_other_lover,
        )
        game_type = loaded_modules["game_type"]
        self._setup_npcs(fresh_cache, game_type, [1, 2, 3], lover_npc_id=2)

        # 以 character_id=1 询问（NPC 2 是恋人，且不是 character_id=1）
        result = handle_player_have_other_lover(1)
        assert result == 1, f"应检测到有其他恋人（NPC 2），实际: {result}"

    def test_player_have_other_lover_excludes_self(self, loaded_modules, fresh_cache):
        """
        输入：只有调用者自己（NPC 1）有爱情陷落素质
        回傳：无
        功能：验证 handle_player_have_other_lover 正确排除 character_id 本身，
              排除后找不到其他恋人，返回 0。
        """
        from Script.Design.handle_premise.handle_premise_fall import (
            handle_player_have_other_lover,
        )
        game_type = loaded_modules["game_type"]
        self._setup_npcs(fresh_cache, game_type, [1, 2, 3], lover_npc_id=1)

        # character_id=1 询问，自己被排除，其他 NPC 无陷落
        result = handle_player_have_other_lover(1)
        assert result == 0, f"排除自己后应无其他恋人，实际: {result}"

    def test_player_no_other_lover_is_logical_negation(self, loaded_modules, fresh_cache):
        """
        输入：cache 中 NPC 2 有爱情陷落（不是 character_id=3）
        回傳：无
        功能：验证 handle_player_no_other_lover 是 handle_player_have_other_lover 的逻辑取反。
        """
        from Script.Design.handle_premise.handle_premise_fall import (
            handle_player_have_other_lover,
            handle_player_no_other_lover,
        )
        game_type = loaded_modules["game_type"]
        self._setup_npcs(fresh_cache, game_type, [1, 2, 3], lover_npc_id=2)

        # character_id=3 询问（不排除 NPC 2）
        have_lover = handle_player_have_other_lover(3)
        no_lover = handle_player_no_other_lover(3)

        assert bool(have_lover) != bool(no_lover), (
            f"no_other_lover 应为 have_other_lover 的取反: "
            f"have={have_lover}, no={no_lover}"
        )

    def test_different_character_ids_produce_different_results(self, loaded_modules, fresh_cache):
        """
        输入：cache 中 NPC 2 有爱情陷落
        回傳：无
        功能：验证 handle_player_have_other_lover 对不同 character_id 给出不同结果——
              character_id=2（被排除自己）应返回 0；character_id=3（不排除 NPC 2）应返回 1。
              这证明结果是 character_id 相关的，不可跨 character_id 共用缓存。
        """
        from Script.Design.handle_premise.handle_premise_fall import (
            handle_player_have_other_lover,
        )
        game_type = loaded_modules["game_type"]
        self._setup_npcs(fresh_cache, game_type, [1, 2, 3], lover_npc_id=2)

        result_as_2 = handle_player_have_other_lover(2)  # 排除自己（NPC 2 被排除）
        result_as_3 = handle_player_have_other_lover(3)  # 不排除 NPC 2

        assert result_as_2 == 0, (
            f"character_id=2 询问时应排除自己，结果应为 0，实际: {result_as_2}"
        )
        assert result_as_3 == 1, (
            f"character_id=3 询问时 NPC 2 是恋人，结果应为 1，实际: {result_as_3}"
        )

    def test_npc_traversal_cached_within_one_pass(self, loaded_modules, fresh_cache):
        """
        输入：以 get_weight_from_premise_dict 连续两次评估同一遍历型前提（共用缓存）
        回傳：无
        功能：验证在单趟内，NPC 遍历型前提不会被重复执行（计数器验证只调用一次）。
        """
        handle_premise = loaded_modules["handle_premise"]
        constant = loaded_modules["constant"]
        game_type = loaded_modules["game_type"]

        # 准备 NPC（无陷落）
        self._setup_npcs(fresh_cache, game_type, [1, 2])

        call_count = {"n": 0}
        original_handler = constant.handle_premise_data.get("player_have_other_lover")

        def counting_handler(cid):
            call_count["n"] += 1
            return original_handler(cid) if original_handler else 0

        constant.handle_premise_data["player_have_other_lover"] = counting_handler

        # 确保 NPC 1 有 behavior 数据，避免 get_weight_from_premise_dict 中 gag 检查失败
        # （character_id=1 的角色已在 _setup_npcs 中创建）
        try:
            premise_set = frozenset({"player_have_other_lover"})
            calc_dict = {}

            w1, calc_dict = handle_premise.get_weight_from_premise_dict(
                premise_set, 1, calc_dict
            )
            w2, calc_dict = handle_premise.get_weight_from_premise_dict(
                premise_set, 1, calc_dict  # 复用同一趟缓存
            )

            assert w1 == w2, f"两次评估结果应相同: {w1} != {w2}"
            assert call_count["n"] == 1, (
                f"NPC 遍历型前提在单趟内只应被实际调用一次，被调用了 {call_count['n']} 次"
            )
        finally:
            if original_handler is not None:
                constant.handle_premise_data["player_have_other_lover"] = original_handler
            else:
                del constant.handle_premise_data["player_have_other_lover"]

    def test_player_have_other_pet_detects_pet(self, loaded_modules, fresh_cache):
        """
        输入：cache 中 NPC 2 有隶属陷落3级素质
        回傳：无
        功能：验证 handle_player_have_other_pet 正确识别出存在宠物。
        """
        from Script.Design.handle_premise.handle_premise_fall import (
            handle_player_have_other_pet,
        )
        game_type = loaded_modules["game_type"]

        # 隶属系陷落 1 级（211）且 3 级（213）
        gc = getattr(fresh_cache, "_test_game_config", None)
        for cid in [1, 2, 3]:
            npc = _make_npc(game_type, cid, game_config_mod=gc)
            if cid == 2:
                npc.talent[211] = 1
                npc.talent[213] = 1
            fresh_cache.character_data[cid] = npc
            fresh_cache.npc_id_got.add(cid)

        result = handle_player_have_other_pet(1)
        assert result == 1, f"应检测到存在宠物（NPC 2），实际: {result}"


# ── 测试 4：handle_have_moved 副作用文档测试 ──────────────────────────────────

class TestHaveMovedSideEffect:
    """
    文档测试：确认 handle_have_moved 有副作用（写入 action_info.last_move_time），
    因此不可跨调用缓存其结果。
    """

    def test_handle_have_moved_writes_last_move_time(self, loaded_modules, fresh_cache):
        """
        输入：NPC，其 last_move_time 早于当前 behavior.start_time（同天，小时更早）
        回傳：无
        功能：确认 handle_have_moved 调用后，character_data.action_info.last_move_time
               被更新为 behavior.start_time——证明该函数有副作用（不可安全缓存跨调用）。
        """
        hp_other = loaded_modules["hp_other"]
        game_type = loaded_modules["game_type"]
        gc = getattr(fresh_cache, "_test_game_config", None)

        npc = _make_npc(game_type, 10, game_config_mod=gc)
        # start_time 为今天 10 点
        npc.behavior.start_time = datetime.datetime(2, 1, 1, 10, 0)
        # last_move_time 为今天 8 点（更早，同天）
        npc.action_info.last_move_time = datetime.datetime(2, 1, 1, 8, 0)
        fresh_cache.character_data[10] = npc
        fresh_cache.npc_id_got.add(10)

        original_last_move_time = datetime.datetime(2, 1, 1, 8, 0)

        result = hp_other.handle_have_moved(10)

        assert result == 1, f"应判定为已移动（过了 1 小时），实际: {result}"
        assert npc.action_info.last_move_time != original_last_move_time, (
            "handle_have_moved 应已更新 last_move_time（有副作用）"
        )
        assert npc.action_info.last_move_time == npc.behavior.start_time, (
            "last_move_time 应被更新为 behavior.start_time"
        )

    def test_handle_have_moved_side_effect_invalidates_cached_result(
        self, loaded_modules, fresh_cache
    ):
        """
        输入：调用 handle_have_moved 两次（相同参数）
        回傳：无
        功能：证明 handle_have_moved 第一次调用后，由于副作用（更新了 last_move_time），
               第二次调用的条件已不满足，因此两次结果不同（1 → 0）。
               这是「不可跨调用缓存该函数」的直接证据。
        """
        hp_other = loaded_modules["hp_other"]
        game_type = loaded_modules["game_type"]
        gc = getattr(fresh_cache, "_test_game_config", None)

        npc = _make_npc(game_type, 11, game_config_mod=gc)
        npc.behavior.start_time = datetime.datetime(2, 1, 1, 10, 0)
        npc.action_info.last_move_time = datetime.datetime(2, 1, 1, 8, 0)
        fresh_cache.character_data[11] = npc
        fresh_cache.npc_id_got.add(11)

        result1 = hp_other.handle_have_moved(11)
        result2 = hp_other.handle_have_moved(11)

        assert result1 == 1, f"第一次调用：应为 1（已移动），实际: {result1}"
        assert result2 == 0, (
            f"第二次调用：副作用后 last_move_time 已更新，条件不再满足，应为 0，实际: {result2}"
        )
        # 关键结论：如果缓存了 result1 并复用，会得到错误的 1（脏缓存）


# ── 测试 5：search_target 风格的 premise_data 跨调用复用模拟验证 ───────────────

class TestPremiseDataCrossCallReuse:
    """
    验证 search_target / find_character_target 中，premise_data 字典在
    多次 search_target 调用间正确共享，同一前提不被重复评估。
    """

    def _simulate_search(self, premise_id: str, character_id: int, premise_data: dict):
        """
        输入：前提 id、角色 id、共用的 premise_data 字典
        回傳：int，前提权重
        功能：模拟 search_target 中对单个前提的评估与缓存逻辑（与源码完全对应）。
        """
        from Script.Design import handle_premise as hp_module
        if premise_id in premise_data:
            return premise_data[premise_id]
        result = hp_module.handle_premise(premise_id, character_id)
        result = max(result, 0)
        premise_data[premise_id] = result
        return result

    def test_premise_evaluated_once_across_two_search_calls(
        self, loaded_modules, fresh_cache
    ):
        """
        输入：模拟两次 search_target 调用，共用同一 premise_data 字典
        回傳：无
        功能：确认同一前提在共用的 premise_data 中只被处理器实际调用一次。
        """
        constant = loaded_modules["constant"]

        call_count = {"n": 0}
        fake_premise = "__test_cross_call__"
        constant.handle_premise_data[fake_premise] = lambda cid: (
            call_count.update({"n": call_count["n"] + 1}) or 1
        )

        try:
            premise_data = {}  # 模拟一次 find_character_target 的 premise_data

            # 第一次 search_target 调用
            r1 = self._simulate_search(fake_premise, 0, premise_data)
            count_after_first = call_count["n"]

            # 第二次 search_target 调用（共用 premise_data）
            r2 = self._simulate_search(fake_premise, 0, premise_data)
            count_after_second = call_count["n"]

            assert r1 == 1 and r2 == 1
            assert count_after_first == 1, f"第一次应调用一次处理器，实际: {count_after_first}"
            assert count_after_second == 1, (
                f"第二次应命中缓存（不调用处理器），累计仍应为 1，实际: {count_after_second}"
            )
        finally:
            del constant.handle_premise_data[fake_premise]

    def test_independent_passes_have_independent_premise_dicts(
        self, loaded_modules, fresh_cache
    ):
        """
        输入：两次独立「趟次」，各自创建新的 premise_data = {}
        回傳：无
        功能：确认两次独立趟次完全隔离，状态改变后第二趟能正确反映新状态（不洩漏）。
        """
        constant = loaded_modules["constant"]

        state_flag = {"value": 0}
        fake_premise = "__test_independent_pass__"
        constant.handle_premise_data[fake_premise] = lambda cid: state_flag["value"]

        try:
            # 趟次 1：状态为 0
            state_flag["value"] = 0
            premise_data_pass1 = {}
            r1 = self._simulate_search(fake_premise, 0, premise_data_pass1)
            assert r1 == 0, f"趟次 1 应为 0，实际: {r1}"

            # 改变状态
            state_flag["value"] = 1

            # 趟次 2：独立的 premise_data（新趟次，清空缓存）
            premise_data_pass2 = {}
            r2 = self._simulate_search(fake_premise, 0, premise_data_pass2)
            assert r2 == 1, f"趟次 2 应反映新状态 1，实际: {r2}"

            # 确认两个 dict 独立且各自记录了正确值
            assert premise_data_pass1 is not premise_data_pass2
            assert premise_data_pass1.get(fake_premise) == 0
            assert premise_data_pass2.get(fake_premise) == 1
        finally:
            del constant.handle_premise_data[fake_premise]
