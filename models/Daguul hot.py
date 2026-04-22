"""
Python model 'Daguul hot.py'
Translated using PySD
"""

from pathlib import Path
import numpy as np

from pysd.py_backend.functions import if_then_else
from pysd.py_backend.statefuls import Integ
from pysd.py_backend.lookups import HardcodedLookups
from pysd import Component

__pysd_version__ = "3.14.3"

__data = {"scope": None, "time": lambda: 0}

_root = Path(__file__).parent


component = Component()

#######################################################################
#                          CONTROL VARIABLES                          #
#######################################################################

_control_vars = {
    "initial_time": lambda: 0,
    "final_time": lambda: 40,
    "time_step": lambda: 1,
    "saveper": lambda: time_step(),
}


def _init_outer_references(data):
    for key in data:
        __data[key] = data[key]


@component.add(name="Time")
def time():
    """
    Current time of the model.
    """
    return __data["time"]()


@component.add(
    name="FINAL TIME", units="Year", comp_type="Constant", comp_subtype="Normal"
)
def final_time():
    """
    The final time for the simulation.
    """
    return __data["time"].final_time()


@component.add(
    name="INITIAL TIME", units="Year", comp_type="Constant", comp_subtype="Normal"
)
def initial_time():
    """
    The initial time for the simulation.
    """
    return __data["time"].initial_time()


@component.add(
    name="SAVEPER",
    units="Year",
    limits=(0.0, np.nan),
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"time_step": 1},
)
def saveper():
    """
    The frequency with which output is stored.
    """
    return __data["time"].saveper()


@component.add(
    name="TIME STEP",
    units="Year",
    limits=(0.0, np.nan),
    comp_type="Constant",
    comp_subtype="Normal",
)
def time_step():
    """
    The time step for the simulation.
    """
    return __data["time"].time_step()


#######################################################################
#                           MODEL VARIABLES                           #
#######################################################################


@component.add(
    name="Сургуулийн насны хүүхэд",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__63": 1},
)
def nvs_():
    return nvs__63() * 0.23


@component.add(
    name="Шаардлагатай сургуулийн тоо",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs_": 1},
)
def nvs__1():
    """
    Нэг сургуулийг 940 хүүхдийн хүчин чадалтайгаар тооцсон
    """
    return nvs_() / 940


@component.add(
    name="Шаардлагатай цэцэрлэгийн тоо",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__3": 1},
)
def nvs__2():
    """
    Нэг цэцэрлэгийн хүчин чадлыг 240 хүүхдийн чадлаар тооцсон
    """
    return nvs__3() / 240


@component.add(
    name="Цэцэрлэгийн насны хүүхэд",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__63": 1},
)
def nvs__3():
    return nvs__63() * 0.1


@component.add(
    name="Нийт хүн ам",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__21": 1, "nvs__5": 1, "nvs_": 1, "nvs__3": 1},
)
def nvs__4():
    return nvs__21() + nvs__5() + nvs_() + nvs__3()


@component.add(
    name="Бусад хүн ам",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__63": 1},
)
def nvs__5():
    return nvs__63() * 0.37


@component.add(
    name="Аж ахуйн нэгжийн эрхлэх газар",
    units="km*km",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__36": 1},
)
def nvs__6():
    """
    Талбай*Бизнесийн газрын хэсэг
    """
    return nvs__36()


@component.add(
    name="Байшин барих газар",
    units="km*km",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__30": 1},
)
def nvs__7():
    """
    Байшингийн газрын хэсэг*Талбай
    """
    return nvs__30()


@component.add(
    name="Аж ахуйн нэгж",
    units="company/Year",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__35": 1, "nvs__46": 1, "nvs__14": 1, "nvs__11": 1},
)
def nvs__8():
    return nvs__35() * nvs__46() * nvs__14() + nvs__11()


@component.add(
    name="Аж ахуйн нэмэгдэх он",
    limits=(0.0, 1.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__9():
    return 0


@component.add(
    name="Нэмэгдэх аж ахуйн нэгж",
    limits=(0.0, 1000.0, 10.0),
    comp_type="Lookup",
    comp_subtype="Normal",
    depends_on={"__lookup__": "_hardcodedlookup_nvs_10"},
)
def nvs__10(x, final_subs=None):
    return _hardcodedlookup_nvs_10(x, final_subs)


_hardcodedlookup_nvs_10 = HardcodedLookups(
    [2, 3, 4, 5, 6, 7, 8],
    [55, 70, 70, 70, 70, 70, 0],
    {},
    "interpolate",
    {},
    "_hardcodedlookup_nvs_10",
)


@component.add(
    name="Нийт нэмэгдэх аж ахуйн нэгж",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__9": 1, "nvs__10": 1, "time": 1},
)
def nvs__11():
    """
    IF THEN ELSE(Time=Аж ахуйн нэмэгдэх он, Нэмэгдэх аж ахуйн нэгж, 0)
    """
    return if_then_else(nvs__9() == 1, lambda: nvs__10(time()), lambda: 0)


@component.add(
    name="Бизнесийн татвар",
    units="tax/company",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__71": 1, "nvs__35": 1},
)
def nvs__12():
    return nvs__71() * nvs__35()


@component.add(
    name="ААН ийн өсөх чадвар",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="with Lookup",
    depends_on={"nvs__22": 1},
)
def nvs__13():
    return np.interp(
        nvs__22(),
        [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0],
        [0.2, 0.25, 0.35, 0.5, 0.7, 1.0, 1.35, 1.6, 1.8, 1.95, 2.0],
    )


@component.add(
    name="Аж ахуйн нэгжийн татах чадвар",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__13": 1, "nvs__37": 1, "nvs__61": 1},
)
def nvs__14():
    return nvs__13() * nvs__37() * nvs__61()


@component.add(
    name="Татах чадвар",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__64": 1, "nvs__78": 1, "nvs__62": 1, "nvs__18": 1},
)
def nvs__15():
    return nvs__64() * nvs__78() * nvs__62() * nvs__18()


@component.add(
    name="Орон сууцны татах чадвар нэмэх",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__17": 1},
)
def nvs__16():
    return nvs__17()


@component.add(
    name="Орон сууцны газрын татах чадвар",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="with Lookup",
    depends_on={"nvs__31": 1},
)
def nvs__17():
    return np.interp(
        nvs__31(),
        [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        [0.4, 0.7, 1.0, 1.25, 1.45, 1.5, 1.5, 1.4, 1.0, 0.5, 0.0],
    )


@component.add(
    name="ААН ийн татах чадвар",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="with Lookup",
    depends_on={"nvs__22": 1},
)
def nvs__18():
    return np.interp(
        nvs__22(),
        [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0],
        [2.0, 1.95, 1.8, 1.6, 1.35, 1.0, 0.5, 0.3, 0.2, 0.15, 0.1],
    )


@component.add(
    name="Аж ахуйн нэгжийн бүтэц бүрт газар",
    units="km*km/company",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__19():
    return 0.002


@component.add(
    name="Аж ахуйн нэгжийн эзэмших газар",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__35": 1, "nvs__19": 1, "nvs__6": 1},
)
def nvs__20():
    return (nvs__35() * nvs__19()) / nvs__6()


@component.add(
    name="Ажиллах хүч",
    units="people",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__63": 1, "nvs__66": 1},
)
def nvs__21():
    return nvs__63() * nvs__66()


@component.add(
    name="Ажиллах хүчний ажлын харьцаа",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__21": 1, "nvs__23": 1},
)
def nvs__22():
    return nvs__21() / nvs__23()


@component.add(
    name="Ажлын байр",
    units="people",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__35": 1, "nvs__34": 1},
)
def nvs__23():
    return nvs__35() * nvs__34()


@component.add(
    name="Анхны аж ахуйн нэгж",
    units="company",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__24():
    return 125


@component.add(
    name="Анхны орон сууц", units="house", comp_type="Constant", comp_subtype="Normal"
)
def nvs__25():
    """
    2660
    """
    return 2660


@component.add(
    name="Анхны хүн ам", units="people", comp_type="Constant", comp_subtype="Normal"
)
def nvs__26():
    """
    7625
    """
    return 7625


@component.add(
    name="Орон сууц",
    units="house",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_nvs_27": 1},
    other_deps={
        "_integ_nvs_27": {
            "initial": {"nvs__25": 1},
            "step": {"nvs__59": 1, "nvs__60": 1},
        }
    },
)
def nvs__27():
    return _integ_nvs_27()


_integ_nvs_27 = Integ(lambda: nvs__59() - nvs__60(), lambda: nvs__25(), "_integ_nvs_27")


@component.add(
    name="Байшин бүрт газар",
    units="km*km/house",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__28():
    """
    0.001
    """
    return 0.006


@component.add(
    name='"Байшин, өрхийн харьцаа"',
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__27": 1, "nvs__65": 1},
)
def nvs__29():
    return nvs__27() / nvs__65()


@component.add(
    name="Суурьшлийн бүс", units="km*km", comp_type="Constant", comp_subtype="Normal"
)
def nvs__30():
    return 243


@component.add(
    name="Байшингийн газрын эзэмшил хэсэг",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__28": 1, "nvs__27": 1, "nvs__7": 1},
)
def nvs__31():
    return (nvs__28() * nvs__27()) / nvs__7()


@component.add(
    name="Нийт талбай", units="km*km", comp_type="Constant", comp_subtype="Normal"
)
def nvs__32():
    return 333


@component.add(
    name="Аж ахуйн нэгжийн бууралт",
    units="company/Year",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__45": 1, "nvs__35": 1},
)
def nvs__33():
    return nvs__45() * nvs__35()


@component.add(
    name="Нэг ААН хамаарах ажлын байр",
    units="people/company",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__34():
    return 20


@component.add(
    name="ААН",
    units="company",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_nvs_35": 1},
    other_deps={
        "_integ_nvs_35": {
            "initial": {"nvs__24": 1},
            "step": {"nvs__8": 1, "nvs__33": 1},
        }
    },
)
def nvs__35():
    return _integ_nvs_35()


_integ_nvs_35 = Integ(lambda: nvs__8() - nvs__33(), lambda: nvs__24(), "_integ_nvs_35")


@component.add(
    name="Аж ахуйн нэгжийн бүс",
    units="km*km",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__36():
    return 90


@component.add(
    name="Аж ахуйн нэгжийн татах чадвар газрын нөлөө",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="with Lookup",
    depends_on={"nvs__20": 1},
)
def nvs__37():
    return np.interp(
        nvs__20(),
        [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        [1.0, 1.15, 1.3, 1.4, 1.45, 1.4, 1.3, 0.9, 0.5, 0.25, 0.0],
    )


@component.add(
    name="Шаардлагатай үйлчилгээний байгууламж",
    units="sf",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__57": 1, "nvs__42": 1},
)
def nvs__38():
    return nvs__57() - nvs__42()


@component.add(
    name="Шилжин ирэлт",
    units="people/Year",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__54": 1, "nvs__63": 1, "nvs__51": 1, "nvs__15": 1},
)
def nvs__39():
    return (nvs__54() + nvs__63()) * nvs__51() * nvs__15()


@component.add(
    name="Шилжин явалт",
    units="people/Year",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__52": 1, "nvs__63": 1},
)
def nvs__40():
    return nvs__52() * nvs__63()


@component.add(
    name="Ердийн орон сууц нураах",
    units="1/Year",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__41():
    return 0.04


@component.add(
    name="Үйлчилгээний байгууламж чанар",
    units="Dmnl",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_nvs_42": 1},
    other_deps={
        "_integ_nvs_42": {
            "initial": {"nvs__70": 1},
            "step": {"nvs__43": 1, "nvs__44": 1},
        }
    },
)
def nvs__42():
    return _integ_nvs_42()


_integ_nvs_42 = Integ(lambda: nvs__43() - nvs__44(), lambda: nvs__70(), "_integ_nvs_42")


@component.add(
    name="Үйлчилгээний байгууламж барих",
    units="sf/Year",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__38": 1, "nvs__82": 1},
)
def nvs__43():
    return nvs__38() * nvs__82()


@component.add(
    name="Үйлчилгээний байгууламж нураах",
    units="sf/Year",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__83": 1, "nvs__42": 1},
)
def nvs__44():
    return nvs__83() * nvs__42()


@component.add(
    name="Аж ахуйн нэгж буурах хувь",
    units="1/Year",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__45():
    return 0.025


@component.add(
    name="Аж ахуйн нэгж нэмэгдэх",
    units="1/Year",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__46():
    return 0.03


@component.add(
    name="Ердийн нас баралт",
    units="1/Year",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__47():
    return 0.007


@component.add(
    name="Ердийн орон сууц барих",
    units="1/Year",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__48():
    return 0.2


@component.add(
    name="Төрөлт",
    units="people/Year",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__50": 1, "nvs__63": 1},
)
def nvs__49():
    return nvs__50() * nvs__63()


@component.add(
    name="Ердийн төрөлт", units="1/Year", comp_type="Constant", comp_subtype="Normal"
)
def nvs__50():
    return 0.009


@component.add(
    name="Ердийн шилжин ирэлт",
    units="1/Year",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__51():
    return 0.085


@component.add(
    name="Ердийн шилжин явалт",
    units="1/Year",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__52():
    return 0.07


@component.add(
    name="Зорчигч",
    units="people",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__23": 1, "nvs__21": 1},
)
def nvs__53():
    return nvs__23() - nvs__21()


@component.add(
    name="Ирээдүйн шилжин ирэх хүн ам",
    units="people",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__53": 1, "nvs__66": 1},
)
def nvs__54():
    return nvs__53() / nvs__66()


@component.add(
    name="Нас баралт",
    units="people/Year",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__47": 1, "nvs__63": 1},
)
def nvs__55():
    return nvs__47() * nvs__63()


@component.add(
    name="Үйлчилгээний байгууламжийн тав тухтай байдал",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__42": 1, "nvs__68": 1, "nvs__63": 1},
)
def nvs__56():
    return (nvs__42() * nvs__68()) / nvs__63()


@component.add(
    name="Объектив үйлчилгээний байгууламж",
    units="sf",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__63": 1, "nvs__53": 1, "nvs__68": 1},
)
def nvs__57():
    return (nvs__63() + nvs__53()) / nvs__68()


@component.add(
    name="Өрхийн хэмжээ",
    units="people/house",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__58():
    return 3


@component.add(
    name="Орон сууц барих",
    units="house/Year",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__67": 1, "nvs__16": 1, "nvs__48": 1},
)
def nvs__59():
    return nvs__67() * nvs__16() * nvs__48()


@component.add(
    name="Орон сууц нураах",
    units="house/Year",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__27": 1, "nvs__41": 1},
)
def nvs__60():
    return nvs__27() * nvs__41()


@component.add(
    name="Хүртээмжтэй байдал", units="Dmnl", comp_type="Constant", comp_subtype="Normal"
)
def nvs__61():
    return 1


@component.add(
    name="Орон сууцны татах чадвар",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="with Lookup",
    depends_on={"nvs__29": 1},
)
def nvs__62():
    return np.interp(
        nvs__29(),
        [0.0, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0, 2.0],
        [
            0.5,
            0.502,
            0.522,
            0.547,
            0.578,
            0.615,
            0.655,
            0.705,
            0.765,
            0.828,
            0.907,
            1.0,
            0.5,
        ],
    )


@component.add(
    name="Хүн ам",
    units="people",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_nvs_63": 1},
    other_deps={
        "_integ_nvs_63": {
            "initial": {"nvs__26": 1},
            "step": {"nvs__49": 1, "nvs__39": 1, "nvs__55": 1, "nvs__40": 1},
        }
    },
)
def nvs__63():
    return _integ_nvs_63()


_integ_nvs_63 = Integ(
    lambda: nvs__49() + nvs__39() - nvs__55() - nvs__40(),
    lambda: nvs__26(),
    "_integ_nvs_63",
)


@component.add(
    name="Үйлчилгээний байгууламжийн татах чадар",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="with Lookup",
    depends_on={"nvs__56": 1},
)
def nvs__64():
    return np.interp(
        nvs__56(),
        [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.58596, 1.8, 2.0],
        [0.5, 0.55, 0.66, 0.8, 1.0, 1.2, 1.4, 1.65, 1.83333, 1.95, 2.0],
    )


@component.add(
    name="Тэнцвэртэй орон сууцны тоо",
    units="house",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__63": 1, "nvs__58": 1},
)
def nvs__65():
    return nvs__63() / nvs__58()


@component.add(
    name="Хөдөлмөрийн оролцоо",
    units="Dmnl",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__66():
    return 0.3


@component.add(
    name="Шаардлагатай орон сууц",
    units="house",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__65": 1, "nvs__27": 1},
)
def nvs__67():
    return nvs__65() - nvs__27()


@component.add(
    name="Үйлчилгээний байгууламжийн хүн ам хэвийн",
    units="people/sf",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__68():
    return 7625


@component.add(
    name="Хүн амын татвар",
    units="tax",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__63": 1, "nvs__79": 1},
)
def nvs__69():
    return nvs__63() * nvs__79()


@component.add(
    name="Анхны үйлчилгээний байгууламжийн чанар",
    units="sf",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__70():
    return 0.5


@component.add(
    name="Безнесийн бүтцэд ногдох татвар",
    units="tax",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__71():
    return 300


@component.add(
    name="Боловсролын салбар",
    units="Dmnl",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_nvs_72": 1},
    other_deps={
        "_integ_nvs_72": {
            "initial": {"nvs__81": 1},
            "step": {"nvs__75": 1, "nvs__74": 1},
        }
    },
)
def nvs__72():
    return _integ_nvs_72()


_integ_nvs_72 = Integ(lambda: nvs__75() - nvs__74(), lambda: nvs__81(), "_integ_nvs_72")


@component.add(
    name="Боловсролын салбарт оруулах халамжийн дундаж",
    units="1/Year",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__73():
    return 0.01


@component.add(
    name="Боловсролын халамж бууруулах",
    units="Dmnl/Year",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__76": 1, "nvs__72": 1},
)
def nvs__74():
    return nvs__76() * nvs__72()


@component.add(
    name="Боловсролын халамж нэмэгдүүлэх",
    units="Dmnl/Year",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__73": 1, "nvs__77": 1, "nvs__72": 1},
)
def nvs__75():
    return nvs__73() * nvs__77() * nvs__72()


@component.add(
    name="Боловсролын халамж хэвийн хэмжээнд",
    units="1/Year",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__76():
    return 0.01


@component.add(
    name="Боловсролын халамжийн зардлын үржүүлэгч",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__80": 1, "nvs__69": 1},
)
def nvs__77():
    return nvs__80() / (nvs__69() * 3)


@component.add(
    name="Боловсролын татах чадвар",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__72": 1},
)
def nvs__78():
    return nvs__72()


@component.add(
    name="Нэг хүнд оногдох татвар",
    units="tax/people",
    limits=(0.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__79():
    return 1


@component.add(
    name="Татварын орлого",
    units="tax",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"nvs__12": 1, "nvs__69": 1},
)
def nvs__80():
    return nvs__12() + nvs__69()


@component.add(
    name="Эхлэл боловсролын халамжийн үнэ цэнэ",
    units="Dmnl",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__81():
    return 1


@component.add(
    name="Үйлчилгээний байгууламж барих дундаж",
    units="1/Year",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__82():
    return 0.07


@component.add(
    name="Үйлчилгээний байгууламжийн дундаж",
    units="1/Year",
    comp_type="Constant",
    comp_subtype="Normal",
)
def nvs__83():
    return 0.025
