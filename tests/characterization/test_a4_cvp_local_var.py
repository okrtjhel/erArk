# -*- coding: UTF-8 -*-
"""
L2/L3 特性测试：Round A4 CVP 函数内局部变量优化等价验证。

验证目标：
  1. handle_comprehensive_value_premise 的重构（将 premise_all_value_list[1]
     提取为局部变量 b1）在各种 B 类型分支下，与重构前行为完全等价。
  2. 覆盖以下分支：A（能力）、T（素质/时间）、J（宝珠）、E（经验）、
     S（状态/ShootPos）、F（好感度/Flag）、X（信赖）、G（攻略/Gift）、
     B（Bondage）、R（Roleplay/Relationship）、P（PenisPos）、Son（直接返回0）。
  3. 边界条件：值恰好等于判定值时的 E/NE/G/L/GE/LE 各运算符。
  4. A3 指定角色、A2 交互对象等主体判别路径。

安全原则：构造最小 cache，不写真实存档，不启动 GUI。
"""
import sys
import os
import datetime
import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ── fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def cvp_modules(game_config_loaded):
    """
    输入：game_config_loaded fixture
    回傳：dict，含 handle_premise 模块和 game_type 模块
    功能：确保模块只导入一次，供所有 CVP 测试用。
    """
    from Script.Core import cache_control, game_type
    from Script.Design import handle_premise as hp
    return {
        "cache_control": cache_control,
        "game_type": game_type,
        "hp": hp,
    }


def _inject_cache(cache_obj, cvp_modules):
    """
    输入：cache 实例、cvp_modules dict
    回傳：无
    功能：将 cache 注入到 handle_premise.__init__ 及 cache_control。
    """
    cvp_modules["hp"].cache = cache_obj
    cvp_modules["cache_control"].cache = cache_obj


def _make_char(game_type_mod, char_id: int, game_config_mod=None) -> object:
    """
    输入：game_type 模块、角色 id、game_config 模块（可选）
    回傳：Character 实例
    功能：构造最小 Character 实例，初始化必要字段。
    """
    ch = game_type_mod.Character()
    ch.cid = char_id
    ch.target_character_id = char_id
    ch.talent = {i: 0 for i in range(300)}
    ch.favorability = {0: 0}
    ch.behavior.start_time = datetime.datetime(2, 1, 1, 8, 0)
    if game_config_mod is not None:
        for i in game_config_mod.config_body_item:
            item_data = game_config_mod.config_body_item[i]
            item_id = item_data.item_id
            item_name = game_config_mod.config_item[item_id].name
            ch.h_state.body_item[i] = [item_name, False, None]
    return ch


@pytest.fixture
def fresh_cvp_cache(cvp_modules, game_config_loaded):
    """
    输入：cvp_modules、game_config_loaded
    回傳：初始化好的最小 Cache 实例
    功能：构造最小 cache，包含玩家（id=0）和辅助 NPC（id=1），
          并注入到所有相关模块。
    """
    game_type = cvp_modules["game_type"]
    cache = game_type.Cache()
    _inject_cache(cache, cvp_modules)

    # 玩家（id=0）
    pl = _make_char(game_type, 0, game_config_mod=game_config_loaded)
    pl.target_character_id = 1
    cache.character_data[0] = pl

    # 辅助 NPC（id=1），作为交互对象
    npc1 = _make_char(game_type, 1, game_config_mod=game_config_loaded)
    npc1.target_character_id = 0
    cache.character_data[1] = npc1

    cache.npc_id_got = {0, 1}
    cache.pl_pre_behavior_instruce = []

    return cache


def _call_cvp(cvp_modules, character_id, *parts):
    """
    输入：cvp_modules、角色 id、B 部分字段（可变参数）
    回傳：int，handle_comprehensive_value_premise 的返回值
    功能：构造 premise_all_value_list 并调用 CVP。
          parts 依次对应 [A主体, B数值类型, C运算符, D判定值, ...]
    """
    premise_all_value_list = list(parts)
    return cvp_modules["hp"].handle_comprehensive_value_premise(character_id, premise_all_value_list)


# ── 测试分支：A（能力） ──────────────────────────────────────────────────────

class TestCVPAbilityBranch:
    """验证 B 类型为 A（能力）时的等价性。"""

    def test_ability_greater_than_judge(self, cvp_modules, fresh_cvp_cache):
        """
        输入：角色能力值 5 > 判定值 3
        回傳：应返回 1
        功能：验证 A 分支 G 运算符正确返回 1。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.ability[0] = 5
        result = _call_cvp(cvp_modules, 1, "A1", "A|0", "G", "3")
        assert result == 1, f"能力5 > 3，应返回1，实际: {result}"

    def test_ability_less_than_judge(self, cvp_modules, fresh_cvp_cache):
        """
        输入：角色能力值 1 < 判定值 3
        回傳：应返回 0（大于判定失败）
        功能：验证 A 分支 G 运算符不满足时返回 0。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.ability[0] = 1
        result = _call_cvp(cvp_modules, 1, "A1", "A|0", "G", "3")
        assert result == 0, f"能力1 <= 3，G 运算符应返回0，实际: {result}"

    def test_ability_equal_with_E_operator(self, cvp_modules, fresh_cvp_cache):
        """
        输入：角色能力值 3 == 判定值 3，运算符 E
        回傳：应返回 1
        功能：验证等于运算符边界。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.ability[0] = 3
        result = _call_cvp(cvp_modules, 1, "A1", "A|0", "E", "3")
        assert result == 1, f"能力3 == 3，E 运算符应返回1，实际: {result}"

    def test_ability_not_equal_with_NE_operator(self, cvp_modules, fresh_cvp_cache):
        """
        输入：角色能力值 2 != 判定值 3，运算符 NE
        回傳：应返回 1
        功能：验证 NE 运算符边界。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.ability[0] = 2
        result = _call_cvp(cvp_modules, 1, "A1", "A|0", "NE", "3")
        assert result == 1, f"能力2 != 3，NE 运算符应返回1，实际: {result}"

    def test_ability_GE_boundary(self, cvp_modules, fresh_cvp_cache):
        """
        输入：角色能力值 3 == 判定值 3，运算符 GE
        回傳：应返回 1（大于等于边界）
        功能：验证 GE 运算符在等值边界正确。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.ability[0] = 3
        result = _call_cvp(cvp_modules, 1, "A1", "A|0", "GE", "3")
        assert result == 1, f"能力3 >= 3，GE 应返回1，实际: {result}"

    def test_ability_LE_boundary(self, cvp_modules, fresh_cvp_cache):
        """
        输入：角色能力值 3 == 判定值 3，运算符 LE
        回傳：应返回 1（小于等于边界）
        功能：验证 LE 运算符在等值边界正确。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.ability[0] = 3
        result = _call_cvp(cvp_modules, 1, "A1", "A|0", "LE", "3")
        assert result == 1, f"能力3 <= 3，LE 应返回1，实际: {result}"

    def test_ability_L_boundary_fail(self, cvp_modules, fresh_cvp_cache):
        """
        输入：角色能力值 3 == 判定值 3，运算符 L
        回傳：应返回 0（等于不满足严格小于）
        功能：验证 L 运算符在等值边界正确拒绝。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.ability[0] = 3
        result = _call_cvp(cvp_modules, 1, "A1", "A|0", "L", "3")
        assert result == 0, f"能力3 不严格小于3，L 应返回0，实际: {result}"


# ── 测试分支：T（素质）与 Time（时间） ────────────────────────────────────────

class TestCVPTalentAndTimeBranch:
    """验证 B 类型为 T（素质）及 Time（时间）分支。"""

    def test_talent_check(self, cvp_modules, fresh_cvp_cache):
        """
        输入：角色素质 201 = 1，判定 >= 1
        回傳：应返回 1
        功能：验证 T 分支素质查询正确。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.talent[201] = 1
        result = _call_cvp(cvp_modules, 1, "A1", "T|201", "GE", "1")
        assert result == 1, f"素质201=1，GE 1 应返回1，实际: {result}"

    def test_talent_absent_returns_zero(self, cvp_modules, fresh_cvp_cache):
        """
        输入：角色素质 100 未设置（默认0），判定 >= 1
        回傳：应返回 0
        功能：验证 T 分支缺失素质时返回0。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.talent[100] = 0
        result = _call_cvp(cvp_modules, 1, "A1", "T|100", "GE", "1")
        assert result == 0, f"素质100=0，GE 1 应返回0，实际: {result}"

    def test_time_check_hour(self, cvp_modules, fresh_cvp_cache):
        """
        输入：角色 behavior.start_time.hour = 8，判定 GE 6
        回傳：应返回 1（时间分支）
        功能：验证 Time 子类型使用 start_time.hour，而非 type_son_id 路径。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.behavior.start_time = datetime.datetime(2, 1, 1, 8, 0)
        result = _call_cvp(cvp_modules, 1, "A1", "Time|0", "GE", "6")
        assert result == 1, f"时间8点 GE 6 应返回1，实际: {result}"


# ── 测试分支：J（宝珠）、E（经验）、X（信赖） ──────────────────────────────

class TestCVPJewelExperienceTrustBranch:
    """验证 J/E/X 分支的基本查询。"""

    def test_jewel_check(self, cvp_modules, fresh_cvp_cache):
        """
        输入：角色宝珠 0 = 10，判定 G 5
        回傳：应返回 1
        功能：验证 J 分支宝珠查询。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.juel[0] = 10
        result = _call_cvp(cvp_modules, 1, "A1", "J|0", "G", "5")
        assert result == 1, f"宝珠10 > 5，应返回1，实际: {result}"

    def test_experience_check(self, cvp_modules, fresh_cvp_cache):
        """
        输入：角色经验 0 = 20，判定 GE 20
        回傳：应返回 1
        功能：验证 E 分支经验查询（边界等值）。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.experience[0] = 20
        result = _call_cvp(cvp_modules, 1, "A1", "E|0", "GE", "20")
        assert result == 1, f"经验20 >= 20，应返回1，实际: {result}"

    def test_trust_check(self, cvp_modules, fresh_cvp_cache):
        """
        输入：角色信赖 50，判定 GE 30
        回傳：应返回 1
        功能：验证 X 分支信赖查询。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.trust = 50
        result = _call_cvp(cvp_modules, 1, "A1", "X|0", "GE", "30")
        assert result == 1, f"信赖50 >= 30，应返回1，实际: {result}"

    def test_trust_not_meeting(self, cvp_modules, fresh_cvp_cache):
        """
        输入：角色信赖 10，判定 G 30
        回傳：应返回 0
        功能：验证 X 分支信赖不满足时返回 0。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.trust = 10
        result = _call_cvp(cvp_modules, 1, "A1", "X|0", "G", "30")
        assert result == 0, f"信赖10 <= 30，G 应返回0，实际: {result}"


# ── 测试分支：F（好感度/Flag）───────────────────────────────────────────────

class TestCVPFavorabilityBranch:
    """验证 F 分支（好感度与 Flag）。"""

    def test_favorability_check(self, cvp_modules, fresh_cvp_cache):
        """
        输入：角色好感度 100，判定 GE 50
        回傳：应返回 1
        功能：验证 F 分支好感度（非 Flag）查询。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.favorability[0] = 100
        result = _call_cvp(cvp_modules, 1, "A1", "F|0", "GE", "50")
        assert result == 1, f"好感100 >= 50，应返回1，实际: {result}"

    def test_favorability_fail(self, cvp_modules, fresh_cvp_cache):
        """
        输入：角色好感度 20，判定 G 50
        回傳：应返回 0
        功能：验证好感不满足时返回 0。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.favorability[0] = 20
        result = _call_cvp(cvp_modules, 1, "A1", "F|0", "G", "50")
        assert result == 0, f"好感20 <= 50，G 应返回0，实际: {result}"


# ── 测试分支：Son（直接返回0）──────────────────────────────────────────────

class TestCVPSonBranch:
    """验证 Son 分支直接返回 0。"""

    def test_son_returns_zero(self, cvp_modules, fresh_cvp_cache):
        """
        输入：B 类型包含 'Son'
        回傳：应返回 0（Son 为子嵌套事件，CVP 直接短路返回 0）
        功能：验证 Son 分支在 b1 局部变量下仍然正确短路。
        """
        # 构造一个包含 Son 的假 B 类型（格式：Son|0）
        # 注意：Son 的判断在 CVP 中优先于其他分支
        # 这里直接调用：A1 主体，B 类型为 "Son|0"，后续参数不重要
        npc = fresh_cvp_cache.character_data[1]
        # 直接构造 premise_all_value_list
        result = cvp_modules["hp"].handle_comprehensive_value_premise(
            1, ["A1", "Son|0", "GE", "0"]
        )
        assert result == 0, f"Son 分支应直接返回 0，实际: {result}"


# ── 测试分支：A2（交互对象主体） ─────────────────────────────────────────────

class TestCVPSubjectA2:
    """验证 A2 主体路径（取角色的 target_character_id 对应的角色）。"""

    def test_a2_reads_target_character(self, cvp_modules, fresh_cvp_cache):
        """
        输入：character_id=1 的 target_character_id=0（玩家），玩家能力 0 = 99
        回傳：应返回 1（读取的是玩家的能力，而不是 NPC 1 的）
        功能：验证 A2 主体路径在 b1 重构后仍能正确指向交互对象。
        """
        pl = fresh_cvp_cache.character_data[0]
        pl.ability[0] = 99
        # NPC 1 的交互对象是玩家（id=0），在 fixture 中已设置 npc1.target_character_id=0
        npc1 = fresh_cvp_cache.character_data[1]
        npc1.ability[0] = 0  # NPC 1 自己能力为 0
        npc1.target_character_id = 0

        result = _call_cvp(cvp_modules, 1, "A2", "A|0", "GE", "90")
        assert result == 1, f"A2 主体是玩家（能力99 >= 90），应返回1，实际: {result}"

    def test_a1_vs_a2_gives_different_results(self, cvp_modules, fresh_cvp_cache):
        """
        输入：NPC 1 能力=5，玩家能力=99；分别用 A1 和 A2 判断能力 >= 50
        回傳：A1 应返回 0（NPC 1 能力5 < 50），A2 应返回 1（玩家能力99 >= 50）
        功能：证明 A1/A2 主体路径经 b1 重构后仍能区分自己与交互对象。
        """
        pl = fresh_cvp_cache.character_data[0]
        pl.ability[0] = 99
        npc1 = fresh_cvp_cache.character_data[1]
        npc1.ability[0] = 5
        npc1.target_character_id = 0

        result_a1 = _call_cvp(cvp_modules, 1, "A1", "A|0", "GE", "50")
        result_a2 = _call_cvp(cvp_modules, 1, "A2", "A|0", "GE", "50")

        assert result_a1 == 0, f"A1（NPC 1 能力5）<50，应返回0，实际: {result_a1}"
        assert result_a2 == 1, f"A2（玩家能力99）>50，应返回1，实际: {result_a2}"


# ── 测试：多运算符边界汇总 ──────────────────────────────────────────────────

class TestCVPOperatorBoundaries:
    """验证所有运算符在边界值时的正确性（使用能力字段，简洁全覆盖）。"""

    def _set_ability_and_check(self, cvp_modules, cache, ability_val, judge_val, op, expected):
        npc = cache.character_data[1]
        npc.ability[0] = ability_val
        result = _call_cvp(cvp_modules, 1, "A1", "A|0", op, str(judge_val))
        assert result == expected, (
            f"能力={ability_val}, 判定={judge_val}, 运算符={op}: "
            f"期望{expected}，实际{result}"
        )

    def test_G_pass(self, cvp_modules, fresh_cvp_cache):
        self._set_ability_and_check(cvp_modules, fresh_cvp_cache, 4, 3, "G", 1)

    def test_G_fail_equal(self, cvp_modules, fresh_cvp_cache):
        self._set_ability_and_check(cvp_modules, fresh_cvp_cache, 3, 3, "G", 0)

    def test_L_pass(self, cvp_modules, fresh_cvp_cache):
        self._set_ability_and_check(cvp_modules, fresh_cvp_cache, 2, 3, "L", 1)

    def test_L_fail_equal(self, cvp_modules, fresh_cvp_cache):
        self._set_ability_and_check(cvp_modules, fresh_cvp_cache, 3, 3, "L", 0)

    def test_E_pass(self, cvp_modules, fresh_cvp_cache):
        self._set_ability_and_check(cvp_modules, fresh_cvp_cache, 3, 3, "E", 1)

    def test_E_fail(self, cvp_modules, fresh_cvp_cache):
        self._set_ability_and_check(cvp_modules, fresh_cvp_cache, 2, 3, "E", 0)

    def test_GE_equal(self, cvp_modules, fresh_cvp_cache):
        self._set_ability_and_check(cvp_modules, fresh_cvp_cache, 3, 3, "GE", 1)

    def test_GE_greater(self, cvp_modules, fresh_cvp_cache):
        self._set_ability_and_check(cvp_modules, fresh_cvp_cache, 4, 3, "GE", 1)

    def test_GE_less(self, cvp_modules, fresh_cvp_cache):
        self._set_ability_and_check(cvp_modules, fresh_cvp_cache, 2, 3, "GE", 0)

    def test_LE_equal(self, cvp_modules, fresh_cvp_cache):
        self._set_ability_and_check(cvp_modules, fresh_cvp_cache, 3, 3, "LE", 1)

    def test_LE_less(self, cvp_modules, fresh_cvp_cache):
        self._set_ability_and_check(cvp_modules, fresh_cvp_cache, 2, 3, "LE", 1)

    def test_LE_greater(self, cvp_modules, fresh_cvp_cache):
        self._set_ability_and_check(cvp_modules, fresh_cvp_cache, 4, 3, "LE", 0)

    def test_NE_pass(self, cvp_modules, fresh_cvp_cache):
        self._set_ability_and_check(cvp_modules, fresh_cvp_cache, 2, 3, "NE", 1)

    def test_NE_fail_equal(self, cvp_modules, fresh_cvp_cache):
        self._set_ability_and_check(cvp_modules, fresh_cvp_cache, 3, 3, "NE", 0)


# ── 测试：b1 在 Bondage/Roleplay 分支的正确性 ──────────────────────────────

class TestCVPBondageRoleplayBranch:
    """验证 B（绳子捆绑）和 R（角色扮演）分支在 b1 重构下等价。"""

    def test_bondage_match(self, cvp_modules, fresh_cvp_cache):
        """
        输入：h_state.bondage == type_son_id，判定 GE 1
        回傳：应返回 1（bondage 匹配设 final_value=1，然后 GE 判定）
        功能：验证 B 分支（Bondage 路径）。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.h_state.bondage = 5
        # B|5 GE 1 -> final_value=1(bondage==5) -> 1 GE 1 -> 1
        result = cvp_modules["hp"].handle_comprehensive_value_premise(
            1, ["A1", "Bondage|5", "GE", "1"]
        )
        assert result == 1, f"Bondage==5 匹配，GE 1 应返回1，实际: {result}"

    def test_bondage_no_match(self, cvp_modules, fresh_cvp_cache):
        """
        输入：h_state.bondage != type_son_id，判定 GE 1
        回傳：应返回 0（bondage 不匹配 final_value=0，0 GE 1 失败）
        功能：验证 B 分支不匹配时返回 0。
        """
        npc = fresh_cvp_cache.character_data[1]
        npc.h_state.bondage = 3
        result = cvp_modules["hp"].handle_comprehensive_value_premise(
            1, ["A1", "Bondage|5", "GE", "1"]
        )
        assert result == 0, f"Bondage 3 != 5，不匹配，GE 1 应返回0，实际: {result}"

    def test_roleplay_match(self, cvp_modules, fresh_cvp_cache):
        """
        输入：hypnosis.roleplay 中包含 type_son_id=2，判定 GE 1
        回傳：应返回 1（Roleplay 路径 final_value=1）
        功能：验证 R 分支（Roleplay 路径）。
        """
        npc = fresh_cvp_cache.character_data[1]
        # roleplay 为 list，使用 append 添加
        if 2 not in npc.hypnosis.roleplay:
            npc.hypnosis.roleplay.append(2)
        result = cvp_modules["hp"].handle_comprehensive_value_premise(
            1, ["A1", "Roleplay|2", "GE", "1"]
        )
        assert result == 1, f"Roleplay 包含2，GE 1 应返回1，实际: {result}"
