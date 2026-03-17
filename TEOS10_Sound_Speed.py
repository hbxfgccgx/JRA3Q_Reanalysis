"""
TEOS-10 (国际热力学海洋方程) 海水声速计算
==============================================

基于国际热力学海洋方程 (TEOS-10) 的海水声速计算原理及公式说明。

TEOS-10 原理说明
-----------------
TEOS-10 (Thermodynamic Equation of Seawater - 2010) 是由国际海洋物理科学协会
(IAPSO) 于 2010 年正式采用的海水热力学标准方程。它采用 Gibbs 函数 g(SA, T, p)
作为核心，所有热力学量均可从该函数导出。

声速公式推导
------------
根据热力学基本关系，海水中声速 c 由等熵压缩率 κ_S 决定：

    c = 1 / sqrt(ρ · κ_S)                                              (1)

其中：
    ρ    = 海水密度 (kg/m³)
    κ_S  = 等熵（绝热）压缩率 (Pa⁻¹)，定义为：

    κ_S = -(1/v) · (∂v/∂P)_{SA, η}                                    (2)

    v    = 比容 (m³/kg)，即密度的倒数
    SA   = 绝对盐度 (g/kg)
    η    = 比熵 (J/(kg·K))
    P    = 绝对压力 (Pa)

利用 Gibbs 函数 g(SA, T, p) 的热力学关系，声速可表达为：

    c² = -v² · (∂P/∂v)_{SA, η} = g_P / (g_TP² / g_TT - g_PP)        (3)

其中下标表示对相应变量的偏导数：
    g_P   = ∂g/∂p          (比容 v = g_P)
    g_PP  = ∂²g/∂p²
    g_TT  = ∂²g/∂T²
    g_TP  = ∂²g/∂T∂p

等价地，利用热力学关系可以将 (3) 改写为更直观的形式：

    c² = (∂P/∂ρ)_{SA, η} = κ_T⁻¹/ρ · (1 + α·T_in_situ/(ρ·Cp·κ_T))  (4)

其中：
    κ_T  = 等温压缩率 (Pa⁻¹)
    α    = 热膨胀系数 (K⁻¹)
    Cp   = 等压热容 (J/(kg·K))

TEOS-10 变量体系
-----------------
TEOS-10 引入以下标准变量：
    SP   : 实用盐度 (Practical Salinity, PSS-78, 无量纲)
    SA   : 绝对盐度 (Absolute Salinity, g/kg) — 海水中溶解物质的真实质量分数
    CT   : 保守温度 (Conservative Temperature, °C) — 与位温不同，是严格保守量
    p    : 海压 (Sea pressure, dbar) — 绝对压力减去标准大气压 (10.1325 dbar)

换算关系：
    SA ≈ SP × 35.16504 / 35 + δSA           (5)
    δSA 为成分异常校正项 (g/kg)

    CT = h₀(SA, θ) / Cp₀                    (6)
    h₀  = 潜热焓 (J/kg), Cp₀ = 3991.86795711963 J/(kg·K)

GSW 库中的声速计算
-------------------
TEOS-10 的 Gibbs 海水 (GSW) Python 库通过拟合的 75 项多项式表达式
高效计算比容 v(SA, CT, p)，并由此推导声速：

    c(SA, CT, p) = sqrt(v / (v_PP - v_P² / v_PP_etc))

实际使用中调用 gsw.sound_speed(SA, CT, p) 直接获得声速 (m/s)。

参考文献
--------
IOC, SCOR and IAPSO, 2010: The international thermodynamic equation of
seawater - 2010: Calculation and use of thermodynamic properties.
Intergovernmental Oceanographic Commission, Manuals and Guides No. 56,
UNESCO (English), 196 pp. https://www.teos-10.org/

McDougall, T.J. and P.M. Barker, 2011: Getting started with TEOS-10 and
the Gibbs Seawater (GSW) Oceanographic Toolbox, 28pp., SCOR/IAPSO WG127.

Roquet, F., G. Madec, T.J. McDougall, and P.M. Barker, 2015: Accurate
polynomial expressions for the density and specific volume of seawater
using the TEOS-10 standard. Ocean Modelling, 90, pp. 29-43.
"""

import numpy as np
import gsw


class TEOS10SoundSpeed:
    """
    基于 TEOS-10 标准计算海水声速。

    主要步骤：
    1. 将实用盐度 SP 转换为绝对盐度 SA
    2. 将原位温度 t 转换为保守温度 CT（可选）
    3. 调用 gsw.sound_speed(SA, CT, p) 计算声速

    声速的物理意义：
        声波在海水中的传播速度，典型值约为 1500 m/s（近表层）。
        声速随温度升高而增大，随盐度升高而增大，随压力（深度）增大而增大。
    """

    # 标准大气压，用于绝对压力与海压的换算 (dbar)
    P_ATM_DBAR = 10.1325

    def __init__(self, lon=None, lat=None):
        """
        初始化计算器。

        Parameters
        ----------
        lon : float or array-like, optional
            经度 (度), -360 到 360。用于 SA 的成分异常校正。
            若不提供则使用全球平均校正。
        lat : float or array-like, optional
            纬度 (度), -90 到 90。
        """
        self.lon = lon
        self.lat = lat

    def practical_to_absolute_salinity(self, SP, p):
        """
        将实用盐度 SP (PSS-78) 转换为绝对盐度 SA (TEOS-10)。

        转换公式（简化）：
            SA ≈ SP × (35.16504 / 35) + δSA(SP, p, lon, lat)

        其中 δSA 是考虑海洋区域成分变化的盐度异常校正项 (g/kg)。
        当无法获取经纬度时，使用全球平均值 (δSA ≈ 0)。

        Parameters
        ----------
        SP : float or array-like
            实用盐度 (PSS-78, 无量纲)
        p : float or array-like
            海压 (dbar)

        Returns
        -------
        SA : float or array-like
            绝对盐度 (g/kg)
        """
        if self.lon is not None and self.lat is not None:
            SA = gsw.SA_from_SP(SP, p, self.lon, self.lat)
        else:
            # 无经纬度时用简单线性换算（忽略成分异常 δSA）
            SA = SP * 35.16504 / 35.0
        return SA

    def in_situ_to_conservative_temperature(self, SA, t, p):
        """
        将原位温度 t 转换为保守温度 CT。

        转换过程（两步）：
        第一步：原位温度 → 位温 θ
            θ 通过绝热上升至参考压力 p_ref=0 时的温度定义。

        第二步：位温 → 保守温度 CT
            CT = h₀(SA, θ) / Cp₀
        其中：
            h₀  = 参考压力下的比焓 (J/kg)
            Cp₀ = 3991.86795711963 J/(kg·K)（TEOS-10 标准值）

        Parameters
        ----------
        SA : float or array-like
            绝对盐度 (g/kg)
        t : float or array-like
            原位温度 (ITS-90, °C)
        p : float or array-like
            海压 (dbar)

        Returns
        -------
        CT : float or array-like
            保守温度 (°C)
        """
        # 原位温度 → 位温
        pt = gsw.pt0_from_t(SA, t, p)
        # 位温 → 保守温度
        CT = gsw.CT_from_pt(SA, pt)
        return CT

    def sound_speed_from_SP_t(self, SP, t, p):
        """
        由实用盐度 SP 和原位温度 t 计算海水声速。

        计算流程：
            SP, t, p  →  SA (绝对盐度)  →  CT (保守温度)
            →  c = gsw.sound_speed(SA, CT, p)

        声速的 TEOS-10 计算公式（基于 Gibbs 函数）：
            c = sqrt(g_P / (g_TP² / g_TT - g_PP))

        Parameters
        ----------
        SP : float or array-like
            实用盐度 (PSS-78, 无量纲)
        t : float or array-like
            原位温度 (ITS-90, °C)
        p : float or array-like
            海压 (dbar)

        Returns
        -------
        c : float or array-like
            声速 (m/s)
        """
        SA = self.practical_to_absolute_salinity(SP, p)
        CT = self.in_situ_to_conservative_temperature(SA, t, p)
        c = gsw.sound_speed(SA, CT, p)
        return c

    def sound_speed_from_SA_CT(self, SA, CT, p):
        """
        由绝对盐度 SA 和保守温度 CT 直接计算海水声速（TEOS-10 标准输入）。

        根据 TEOS-10，声速 c 由等熵压缩率 κ_S 决定：
            c = 1 / sqrt(ρ · κ_S)                           ...(1)

        利用 Gibbs 函数 g(SA, T, p) 可得：
            κ_S = -(g_PP - g_TP² / g_TT) / g_P²            ...(2)
            ρ   = 1 / g_P                                    ...(3)

        代入 (1)：
            c = sqrt(g_P / (g_TP² / g_TT - g_PP))           ...(4)

        GSW 库通过拟合的 75 项多项式高效近似计算上式，
        在"海洋漏斗"(oceanographic funnel) 范围内精度极高。

        Parameters
        ----------
        SA : float or array-like
            绝对盐度 (g/kg)
        CT : float or array-like
            保守温度 (°C)
        p : float or array-like
            海压 (dbar)

        Returns
        -------
        c : float or array-like
            声速 (m/s)
        """
        return gsw.sound_speed(SA, CT, p)

    def sensitivity_analysis(self, SA_ref=35.0, CT_ref=15.0, p_ref=0.0):
        """
        分析声速对盐度、温度和压力的敏感性（一阶近似）。

        经验关系（在典型海洋条件附近）：
            ∂c/∂T  ≈ +3.0 m/s/°C    （温度升高，声速增大）
            ∂c/∂S  ≈ +1.1 m/s/(g/kg)（盐度升高，声速增大）
            ∂c/∂p  ≈ +0.017 m/s/dbar （压力增大，声速增大）

        Parameters
        ----------
        SA_ref : float
            参考绝对盐度 (g/kg), 默认 35.0
        CT_ref : float
            参考保守温度 (°C), 默认 15.0
        p_ref : float
            参考海压 (dbar), 默认 0.0 (海表)

        Returns
        -------
        dict
            包含参考声速和各变量的一阶偏导数（数值估计）
        """
        dSA = 0.1
        dCT = 0.1
        dp = 1.0

        c0 = float(gsw.sound_speed(SA_ref, CT_ref, p_ref))

        dc_dSA = (float(gsw.sound_speed(SA_ref + dSA, CT_ref, p_ref)) - c0) / dSA
        dc_dCT = (float(gsw.sound_speed(SA_ref, CT_ref + dCT, p_ref)) - c0) / dCT
        dc_dp  = (float(gsw.sound_speed(SA_ref, CT_ref, p_ref + dp)) - c0) / dp

        return {
            "c_ref (m/s)":           round(c0, 4),
            "SA_ref (g/kg)":         SA_ref,
            "CT_ref (°C)":           CT_ref,
            "p_ref (dbar)":          p_ref,
            "∂c/∂SA (m/s per g/kg)": round(dc_dSA, 4),
            "∂c/∂CT (m/s per °C)":   round(dc_dCT, 4),
            "∂c/∂p  (m/s per dbar)": round(dc_dp, 6),
        }


def demonstrate_teos10_sound_speed():
    """
    演示 TEOS-10 海水声速计算的完整流程。

    示例场景：典型热带海洋上层水柱
        位置 : 东经 150°, 北纬 20°
        温度 : 原位温度随深度变化
        盐度 : 实用盐度随深度变化
        深度 : 0 ~ 1000 m (对应海压 0 ~ 1000 dbar)
    """
    print("=" * 60)
    print("TEOS-10 海水声速计算示例")
    print("=" * 60)

    # 示例数据：热带太平洋典型剖面
    lon = 150.0   # 经度 (°E)
    lat = 20.0    # 纬度 (°N)

    # 海压 (dbar) — 近似等于深度 (m)
    p = np.array([0.0, 100.0, 200.0, 500.0, 1000.0])

    # 原位温度 (°C, ITS-90)
    t = np.array([28.0, 24.0, 18.0, 8.0, 4.0])

    # 实用盐度 (PSS-78, 无量纲)
    SP = np.array([34.5, 35.0, 35.2, 34.8, 34.6])

    calculator = TEOS10SoundSpeed(lon=lon, lat=lat)

    print("\n[步骤 1] 输入数据")
    print(f"  位置: 经度 {lon}°E, 纬度 {lat}°N")
    print(f"  海压 p (dbar): {p}")
    print(f"  原位温度 t (°C): {t}")
    print(f"  实用盐度 SP: {SP}")

    # 步骤 1：SP → SA
    SA = calculator.practical_to_absolute_salinity(SP, p)
    print(f"\n[步骤 2] 实用盐度 → 绝对盐度")
    print(f"  公式: SA = SP × (35.16504/35) + δSA(lon, lat, p)")
    print(f"  绝对盐度 SA (g/kg): {np.round(SA, 4)}")

    # 步骤 2：t → CT
    CT = calculator.in_situ_to_conservative_temperature(SA, t, p)
    print(f"\n[步骤 3] 原位温度 → 保守温度")
    print(f"  公式: CT = h₀(SA, θ) / Cp₀  (Cp₀ = 3991.87 J/(kg·K))")
    print(f"  保守温度 CT (°C): {np.round(CT, 4)}")

    # 步骤 3：计算声速
    c = calculator.sound_speed_from_SA_CT(SA, CT, p)
    print(f"\n[步骤 4] 计算声速")
    print(f"  公式: c = sqrt(g_P / (g_TP²/g_TT - g_PP))")
    print(f"        其中 g(SA,T,p) 为 Gibbs 函数，下标表示偏导数")
    print(f"  等价形式: c = 1 / sqrt(ρ · κ_S)")
    print(f"        ρ  = 海水密度 (kg/m³)")
    print(f"        κ_S = 等熵压缩率 (Pa⁻¹)")
    print(f"\n  海压 (dbar) | 声速 (m/s)")
    print(f"  " + "-" * 28)
    for pi, ci in zip(p, c):
        print(f"  {pi:>10.1f} | {ci:>12.4f}")

    # 灵敏度分析
    print(f"\n[附] 声速灵敏度分析 (参考条件: SA=35 g/kg, CT=15°C, p=0 dbar)")
    sensitivity = calculator.sensitivity_analysis()
    for key, val in sensitivity.items():
        print(f"  {key}: {val}")

    print("\n" + "=" * 60)
    print("计算完成。声速在海表约 1500~1540 m/s，随深度先减后增。")
    print("=" * 60)

    return p, SA, CT, c


if __name__ == "__main__":
    demonstrate_teos10_sound_speed()
