# AoE2ScenarioParser API Reference 全量（84 页）

> 站点：<https://ksneijders.github.io/AoE2ScenarioParser/#/>（docsify，18 页教程见 11 卷）
> API 文档：<https://ksneijders.github.io/AoE2ScenarioParser/api/index.html>（pdoc 生成，84 个页面）
> 仓库：<https://github.com/KSneijders/AoE2ScenarioParser>（105★，GPL-3.0，2026-11-05）
> 抓取：2026-11-08，BFS 抓全 84 页（17.95 MB HTML），剥离 View Source 代码块后转 Markdown，共 545647 字符。

**与 11 卷的分工**：11 卷是手写教程（怎么用），本卷是 API 签名清单（每个类/方法/枚举成员的确切名字、参数、返回值）。
查"某个参数叫什么、枚举值是什么"看本卷；查"怎么走完一个流程"看 11 卷。

页面清单与体量见文末附录。

## 0. 全站结构

| 分组 | 页面数 | 内容 |
|---|---|---|
| 核心 | 3 | `AoE2Scenario` / `AoE2DEScenario` / `Settings` |
| Managers | 7 | trigger / unit / map / player / option / xs / message |
| 数据对象 | 7 | trigger / effect / condition / variable / unit / terrain_tile / player |
| 支持对象 | 7 | area / tile / trigger_select / trigger_ce_lock / new_effect / new_condition / xs_check |
| datasets（数据表） | 12 | units / buildings / heroes / techs / terrains / projectiles / players / conditions / effects / other |
| datasets/trigger_lists（枚举） | 46 | attribute / object_attribute / action_type / age / … 全部触发器枚举 |
| 其它 | 2 | info_dataset_base / scenario_variant / object_support |

### 版本与关键常量（查这里省得翻正文）

| 项 | 值 | 含义 |
|---|---|---|
| `AoE2Scenario.LATEST_VERSION` | `(1,)` | 基类占位，不用它 |
| `AoE2DEScenario.LATEST_VERSION` | **`(1, 59)`** | 0.9.9 支持的最高场景版本；实测本机存档是 1.54 / 1.53，在支持范围内 |
| `TechInfo.LOOM` | `(22, 6)` | 科技 ID 22 / 图标 ID 6 —— `research_technology(technology=22)` |
| `EffectId.SEND_CHAT` | `3` | `send_chat(string_id=...)` 或 `send_chat(message=...)` |
| `EffectId.RESEARCH_TECHNOLOGY` | `2` | 配 `technology` + `force_research_technology` |
| `EffectId.CHANGE_DIPLOMACY` | `1` | 配 `diplomacy` / `source_player` / `target_player` |
| `EffectId.TRIBUTE` | `5` | 配 `tribute_list` / `quantity` / `source_player` / `target_player` |
| `ConditionId.BRING_OBJECT_TO_AREA` | `1` | 最常用的"把单位带到区域" |
| `empty_attributes`（effect） | 见正文 L3376 | 全部 **84** 个 effect 字段的默认值表（`-1` = 未设，字符串字段 = `''`） |
| `empty_attributes`（condition） | 见正文 L2922 | 全部 **32** 个 condition 字段默认值 |

**字段名不要猜。** effect 的每个字段在正文里以 `Attributes for the <name> effect are:` 后跟一个 `- field_name` 列表的形式存在（共 **103** 个 EffectId、**41** 个 ConditionId），
写代码前先搜这条，比翻 GitHub 源码快。


---

## 快速入口 / 场景对象


### S        = ~S
A type variable (generic) that represents an instance of the AoE2Scenario class or any of its
subclasses (e.g. AoE2DEScenario)

### Func        = ~Func
A type variable (generic) that represents a function

### class     AoE2Scenario:
All scenario objects are derived from this class

### AoE2Scenario(	game_version: str,	scenario_version: str,	source_location: str,	name: str,	variant: AoE2ScenarioParser.datasets.scenario_variant.ScenarioVariant | None = None)

### LATEST_VERSION: Tuple[int, int]        = (1,)

### trigger_manager: AoE2ScenarioParser.objects.managers.trigger_manager.TriggerManager
The trigger manager of the scenario

### unit_manager: AoE2ScenarioParser.objects.managers.unit_manager.UnitManager
The unit manager of the scenario

### map_manager: AoE2ScenarioParser.objects.managers.map_manager.MapManager
The map manager of the scenario

### player_manager: AoE2ScenarioParser.objects.managers.player_manager.PlayerManager
The player manager of the scenario

### message_manager: AoE2ScenarioParser.objects.managers.message_manager.MessageManager
The message manager of the scenario

### def         on_write(self, func: ~Func) -> ~Func:
Register a function to be called on write (intended to be used as a decorator)

### scenario_version_tuple: tuple[int, ...]

### game_version: str

### scenario_version: str

### source_location: str

### structure: Dict

### sections: Dict[str, AoE2ScenarioParser.sections.aoe2_file_section.AoE2FileSection]

### name: str

### uuid: uuid.UUID

### new: AoE2ScenarioParser.scenarios.support.object_factory.ObjectFactory

### actions: AoE2ScenarioParser.scenarios.support.scenario_actions.ScenarioActions

### @classmethod
Creates and returns a default instance of the AoE2Scenario class

Args:
    scenario_version: The scenario version to generate
    game_version:

Returns:
    An instance of the AoE2DEScenario class which is the object representation of the default scenario

### @classmethod
Creates and returns an instance of the AoE2Scenario class from the given scenario file

Args:
    path: The path to the scenario file to create the object from
    game_version: The version of the game to create the object for
    name: The name given to this scenario (defaults to the filename without extension)

Returns:
    An instance of the AoE2Scenario class (or any of its subclasses) which is the object representation of
        the given scenario file

### @staticmethod
Get scenario through a UUID, a related object or the name of a scenario.

Args:
    uuid: The UUID of the scenario
    obj: An object related to a scenario
    name: The name of a scenario

Returns:
    The scenario based on the given identifier, or None

### def         remove_store_reference(self) -> None:
This function is DEPRECATED. No replacement is necessary as the store now uses weak references.
You can safely remove the call to this function.

--- Legacy docstring ---

Removes the reference to this scenario object from the scenario store. Useful (~a must) when reading many
scenarios in a row without needing earlier ones. Python likes to take up a lot of memory.
Removing all references to an object will cause the memory to be cleared up.

Warning: Remove all other references too!
    When using this function it's important to remove all other references to the scenario.
    So if save it in a dict or list, remove it from it.
    If you have variables referencing this scenario that you won't need anymore (and won't overwrite) delete
    them using: del varname.

### def         commit(self) -> None:
Commit the changes to the retriever backend made within the managers.

### def         write_to_file(	self,	filename: str,	skip_reconstruction: bool = False,	skip_validation: bool = False) -> None:
Writes the scenario to a new file with the given filename

Args:
    filename: The location to write the file to
    skip_reconstruction: If reconstruction should be skipped. If true, this will ignore all changes made
        using the managers (For example all changes made using trigger_manager).
    skip_validation: If validation should be skipped. If true, no blocking checks will be done when writing.

Raises:
    ValueError: if the setting DISABLE_ERROR_ON_OVERWRITING_SOURCE is not disabled and the source filename is
        the same as the filename being written to

### def         write_error_file(	self,	filename: str = 'error_file.txt',	trail_generator: AoE2ScenarioParser.helper.incremental_generator.IncrementalGenerator = None) -> None:
Outputs the contents of the entire scenario file in a readable format. An example of the format is given below::

########################### units (1954 * struct:UnitStruct)
############ UnitStruct ############  [STRUCT]
00 00 70 42                 x (1 * f32): 60.0
00 00 70 42                 y (1 * f32): 60.0
00 00 00 00                 z (1 * f32): 0.0
52 05 00 00                 reference_id (1 * s32): 1362
89 02                       unit_const (1 * u16): 649
02                          status (1 * u8): 2
00 00 00 00                 rotation (1 * f32): 0.0
00 00                       initial_animation_frame (1 * u16): 0
ff ff ff ff                 garrisoned_in_id (1 * s32): -1

Args:
    filename: The filename to write the error file to
    trail_generator: Write all the bytes remaining in this generator as a trail

### variant: AoE2ScenarioParser.datasets.scenario_variant.ScenarioVariant


### class     AoE2DEScenario(AoE2ScenarioParser.scenarios.aoe2_scenario.AoE2Scenario):
Used to represent a scenario with version >= 1.36 (DE). It is the main class that is exposed to the user of the API.

### LATEST_VERSION: Tuple[int, int]        = (1, 59)

### trigger_manager: AoE2ScenarioParser.objects.managers.trigger_manager.TriggerManager
The trigger manager of the scenario

### unit_manager: AoE2ScenarioParser.objects.managers.unit_manager.UnitManager
The unit manager of the scenario

### map_manager: AoE2ScenarioParser.objects.managers.map_manager.MapManager
The map manager of the scenario

### xs_manager: AoE2ScenarioParser.objects.managers.xs_manager.XsManager
The XS manager of the scenario

### player_manager: AoE2ScenarioParser.objects.managers.player_manager.PlayerManager
The player manager of the scenario

### message_manager: AoE2ScenarioParser.objects.managers.message_manager.MessageManager
The message manager of the scenario

### option_manager: AoE2ScenarioParser.objects.managers.option_manager.OptionManager

### @classmethod
Creates and returns a default instance of the AoE2DEScenario class

Args:
    scenario_version: The scenario version to generate

Returns:
    An instance of the AoE2DEScenario class which is the object representation of the default scenario

### @classmethod
Creates and returns an instance of the AoE2DEScenario class from the given scenario file

Args:
    path: The path to the scenario file to create the object from
    game_version: The version of the game to create the object for
    name: The name given to this scenario (defaults to the filename without extension)

Returns:
    An instance of the AoE2DEScenario class which is the object representation of the given scenario file


Warning: IMPORT THE MODULE, NOT THE VALUES!
    To change these settings, import the module: from AoE2ScenarioParser import settings.
    Then you can change the settings like: settings.RAISE_ERROR_ON_WARNING = True

If you import the values directly like: from ... import RAISE_ERROR_ON_WARNING
_(not written out because it wouldn't work)_, change the value would overwrite the reference and not the value which
means the change wouldn't transfer to the settings module.

### NOTIFY_UNKNOWN_BYTES        = True
Show a notification of extra bytes being available at the end of the file, so you can notify the maintainer

### PRINT_STATUS_UPDATES        = True
If status updates of what is being read and written should be printed to console

### ALLOW_OVERWRITING_SOURCE        = False
Disable the error being raised when overwriting source scenario

### ALLOW_DIRTY_RETRIEVER_OVERWRITE        = False
If it is allowed to overwrite a retriever that is dirty (it has been changed manually)

### SHOW_VARIANT_WARNINGS        = True
If warnings about incorrect variants should be shown or not

### SHOW_SCENARIO_VERSION_WARNINGS        = True
If warnings about reading multiple scenario versions should be shown or not

### MAIN_CHARSET        = 'utf-8'
The charset used to decode the text in the scenario. If it fails, will try the settings.FALLBACK_CHARSET

### FALLBACK_CHARSET        = 'latin-1'
The charset used to decode the text in the scenario when the settings.MAIN_CHARSET fails

### ENABLE_XS_CHECK_INTEGRATION        = True
If the xs-check integration should be active. If set to False, xs-check will not be used anywhere


---

## Managers（8 个）


### class     TriggerManager(AoE2ScenarioParser.objects.aoe2_object.AoE2Object):
Manager of everything trigger-related.

### def         get_trigger_referencing_ce(	trigger: AoE2ScenarioParser.objects.data_objects.trigger.Trigger) -> List[Union[AoE2ScenarioParser.objects.data_objects.effect.Effect, AoE2ScenarioParser.objects.data_objects.condition.Condition]]:
Get all conditions and effects in a Trigger which reference a trigger.

Args:
    trigger: The trigger object

Returns:
    A list with trigger-referencing conditions and effects

### TriggerManager(	triggers: List[AoE2ScenarioParser.objects.data_objects.trigger.Trigger],	trigger_display_order: List[int],	variables: List[AoE2ScenarioParser.objects.data_objects.variable.Variable] = None,	**kwargs)

### triggers: AoE2ScenarioParser.objects.support.uuid_list.UuidList[AoE2ScenarioParser.objects.data_objects.trigger.Trigger]
All triggers

### trigger_display_order: List[int]
The display order. This is a list of trigger IDs in the display order. NOT execution order!

### variables: List[AoE2ScenarioParser.objects.data_objects.variable.Variable]
All currently renamed variables

### def         copy_trigger_per_player(	self,	from_player: enum.IntEnum,	trigger_select: int | AoE2ScenarioParser.objects.support.trigger_select.TriggerSelect,	change_from_player_only: bool = False,	include_player_source: bool = True,	include_player_target: bool = False,	trigger_ce_lock: AoE2ScenarioParser.objects.support.trigger_ce_lock.TriggerCELock | None = None,	include_gaia: bool = False,	create_copy_for_players: List[enum.IntEnum] = None) -> Dict[AoE2ScenarioParser.datasets.players.PlayerId, AoE2ScenarioParser.objects.data_objects.trigger.Trigger]:
Copies a trigger for all or a selection of players. Every copy will change desired player attributes with it.

Args:
    from_player: The central player this trigger is created for. This is the player that will not get
        a copy.
    trigger_select: The ID of the trigger or an object used to identify which trigger to select.
    change_from_player_only: If set to True,  only change player attributes in effects and conditions that
        are equal to the player defined using the from_player parameter.
    include_player_source: If set to True,  allow player source attributes to be changed while copying.
        Player source attributes are attributes where a player is defined to perform an action such as create an
        object. If set to False these attributes will remain unchanged.
    include_player_target: If set to True,  allow player target attributes to be changed while copying.
        Player target attributes are attributes where a player is defined as the target such as change ownership
        or sending resources. If set to False these attributes will remain unchanged.
    trigger_ce_lock: The TriggerCELock object. Used to lock certain (types) of conditions or
        effects from being changed while copying.
    include_gaia: If True,  GAIA is included in the copied list. (Also when create_copy_for_players is
        defined)
    create_copy_for_players: A list of Players to create a copy for. The from_player will be
        excluded from this list.

Returns:
    A dict with all the new created triggers. The key is the player for which the trigger is
        created using the IntEnum associated with it. Example:
        {PlayerId.TWO: Trigger, PlayerId.FIVE: Trigger}

Raises:
    ValueError: if more than one trigger selection is used. Any of (trigger_index, display_index or trigger)
        Or if Both include_player_source and include_player_target are False

### def         copy_trigger(	self,	trigger_select: int | AoE2ScenarioParser.objects.support.trigger_select.TriggerSelect,	append_after_source: bool = True,	add_suffix: bool = True) -> AoE2ScenarioParser.objects.data_objects.trigger.Trigger:
Creates an exact copy (deepcopy) of this trigger.

Args:
    trigger_select: The ID of the trigger or an object used to identify which trigger to select.
    append_after_source: If the new trigger should be appended below the source trigger
    add_suffix: If the text ' (copy)' should be added after the trigger

Returns:
    The newly copied trigger

### def         copy_trigger_tree_per_player(	self,	from_player: enum.IntEnum,	trigger_select: int | AoE2ScenarioParser.objects.support.trigger_select.TriggerSelect,	change_from_player_only: bool = False,	include_player_source: bool = True,	include_player_target: bool = False,	trigger_ce_lock: AoE2ScenarioParser.objects.support.trigger_ce_lock.TriggerCELock | None = None,	include_gaia: bool = False,	create_copy_for_players: Optional[List[enum.IntEnum]] = None,	group_triggers_by: AoE2ScenarioParser.objects.support.enums.group_by.GroupBy | None = None) -> Dict[enum.IntEnum, List[AoE2ScenarioParser.objects.data_objects.trigger.Trigger]]:
Copies an entire trigger tree for all or a selection of players. Every copy will change desired player
attributes with it. Trigger trees are triggers linked together using (de)activate_trigger effects.

Args:
    from_player: The central player this trigger is created for. This is the player that will not get
        a copy.
    trigger_select: The ID of the trigger or an object used to identify which trigger to select.
    change_from_player_only: If set to True,  only change player attributes in effects and conditions that
        are equal to the player defined using the from_player parameter.
    include_player_source: If set to True,  allow player source attributes to be changed while copying.
        Player source attributes are attributes where a player is defined to perform an action such as create an
        object. If set to False these attributes will remain unchanged.
    include_player_target: If set to True,  allow player target attributes to be changed while copying.
        Player target attributes are attributes where a player is defined as the target such as change ownership
        or sending resources. If set to False these attributes will remain unchanged.
    trigger_ce_lock: The TriggerCELock object. Used to lock certain (types) of conditions or
        effects from being changed while copying.
    include_gaia: If True,  GAIA is included in the copied list. (Also when create_copy_for_players is
        defined)
    create_copy_for_players: A list of Players to create a copy for. The from_player will be
        excluded from this list.
    group_triggers_by: How to group the newly added triggers.

Returns:
    The newly created triggers in a dict using the Player as key and as value with a list of triggers

### def         move_triggers(self, trigger_ids: List[int], insert_index: int) -> None:
Moves the given IDs from anywhere to the split index. This function reorders triggers BUT keeps
(de)activate trigger effects linked properly!

As an example:

[0,1,2,3,4,5,6,7,8]  # Current index order
# Let's move trigger 1, 4, 5 and 6 to location 2
self.move_triggers([1, 4, 5, 6], 2)  # << 2 is an INDEX, not the value
[0,1,4,5,6,2,3,7,8]  # New index order

Args:
    trigger_ids: The trigger IDs to move
    insert_index: The index that defines where to insert the triggers

### def         reorder_triggers(self, new_id_order: List[int] = None) -> None:
Reorder all triggers to a given order of IDs. This function reorders triggers BUT keeps (de)activate trigger
effects linked properly!

Examples:

Moving the 6th trigger to the end of the trigger list::

    [0,1,2,3,4,5,6,7,8]  # Trigger IDs before
    self.reorder_triggers([0,1,2,3,5,4,7,8,6])
    [0,1,2,3,5,4,7,8,6]  # Trigger IDs after

Setting the trigger (execution) order to the current display order::

    self.reorder_triggers(self.trigger_display_order)

Keep in mind that all trigger IDs will get remapped with this function. So trigger_manager.triggers[4] might
result in a different trigger after this function is called in comparison to before.

Args:
    new_id_order: The new trigger order. Uses the current display order when left unused

### def         copy_trigger_tree(	self,	trigger_select: int | AoE2ScenarioParser.objects.support.trigger_select.TriggerSelect) -> List[AoE2ScenarioParser.objects.data_objects.trigger.Trigger]:
Copies an entire trigger tree. Trigger trees are triggers linked together using (de)activate_trigger effects.

Args:
    trigger_select: The ID of the trigger or an object used to identify which trigger to select

Returns:
    The newly created triggers in a list

### def         replace_player(	self,	trigger_select: int | AoE2ScenarioParser.objects.support.trigger_select.TriggerSelect,	to_player: AoE2ScenarioParser.datasets.players.PlayerId,	only_change_from: AoE2ScenarioParser.datasets.players.PlayerId = None,	include_player_source: bool = True,	include_player_target: bool = False,	trigger_ce_lock: AoE2ScenarioParser.objects.support.trigger_ce_lock.TriggerCELock = None) -> AoE2ScenarioParser.objects.data_objects.trigger.Trigger:
Replaces player attributes. Specifically useful if multiple players are used in the same trigger.

Args:
    trigger_select: The ID of the trigger or an object used to identify which trigger to select.
    to_player: The player the attributes are changed to.
    only_change_from: Can only change player attributes if the player is equal to the given value
    include_player_source: If set to True,  allow player source attributes to be changed while replacing.
        Player source attributes are attributes where a player is defined to perform an action such as create an
        object. If set to False these attributes will remain unchanged.
    include_player_target: If set to True,  allow player target attributes to be changed while replacing.
        Player target attributes are attributes where a player is defined as the target such as change ownership
        or sending resources. If set to False these attributes will remain unchanged.
    trigger_ce_lock: The TriggerCELock object. Used to lock certain (types) of conditions or
        effects from being changed.

Returns:
    The given trigger with the proper player attributes changed

### def         add_trigger(	self,	name: str,	description: str | None = None,	description_stid: int | None = None,	display_as_objective: bool | None = None,	short_description: str | None = None,	short_description_stid: int | None = None,	display_on_screen: bool | None = None,	description_order: int | None = None,	enabled: bool | None = None,	looping: bool | None = None,	execute_on_load: bool | None = None,	header: bool | None = None,	mute_objectives: bool | None = None,	conditions: Optional[List] = None,	effects: Optional[List] = None) -> AoE2ScenarioParser.objects.data_objects.trigger.Trigger:
Adds a new trigger to the scenario. Everything that is left empty will be set to in-game editor defaults.

Args:
    name: The name for the trigger
    description: The trigger description
    description_stid: The trigger description string table ID
    display_as_objective: Display the trigger as objective
    short_description: The short trigger description
    short_description_stid: The short trigger description string table ID
    display_on_screen: Display the trigger objective on screen
    description_order: ?
    enabled: If the trigger is enabled from the start.
    looping: If the trigger loops.
    execute_on_load: Run the trigger on map load.
    header: Turn objective into header
    mute_objectives: Mute objectives
    conditions: A list of condition managers
    effects: A list of effect managers

Returns:
    The newly created trigger

### def         import_triggers(	self,	triggers: List[AoE2ScenarioParser.objects.data_objects.trigger.Trigger],	index: int = -1,	deepcopy: bool = True) -> List[AoE2ScenarioParser.objects.data_objects.trigger.Trigger]:
Adds existing trigger objects (from another scenario) to this scenario. Keeping all (de)activate trigger
effects linked!

Args:
    triggers: The list of Trigger objects to be added
    index: The index where to insert the new triggers, will be added at the end when left unused.
    deepcopy: If the given triggers need to be deep copied or not when importing. Can be useful to keep the
        reference alive between the source and target trigger the same when setting this to False.

Returns:
    The newly added triggers (with the new IDs and activation links etc.)

### def         get_trigger(	self,	trigger_select: int | AoE2ScenarioParser.objects.support.trigger_select.TriggerSelect) -> AoE2ScenarioParser.objects.data_objects.trigger.Trigger:
Get a single trigger

Args:
    trigger_select: The ID of the trigger or an object used to identify which trigger to select.

Returns:
    The selected trigger

### def         add_variable(	self,	name: str,	variable_id: int = -1) -> AoE2ScenarioParser.objects.data_objects.variable.Variable:
Adds a variable.

Args:
    name: The name for the variable
    variable_id: The ID of the variable. If left empty lowest available value will be used

Returns:
    The newly renamed Variable

### def         get_variable(	self,	variable_id: int = None,	variable_name: str = None) -> Optional[AoE2ScenarioParser.objects.data_objects.variable.Variable]:
Get a specific variable

Args:
    variable_id: The ID of the variable you want
    variable_name: The name of the variable you want

Returns:
    The Variable object or None if it couldn't be found

### def         remove_trigger(	self,	trigger_select: int | AoE2ScenarioParser.objects.support.trigger_select.TriggerSelect) -> None:
Removes a trigger BUT keeps (de)activate trigger effects linked properly!

Args:
    trigger_select: The ID of the trigger or an object used to identify which trigger to select.

### def         remove_triggers(	self,	trigger_selects: List[int | AoE2ScenarioParser.objects.support.trigger_select.TriggerSelect]) -> None:
Removes a list of triggers BUT keeps (de)activate trigger effects linked properly!

Args:
    trigger_selects: The list with trigger IDs

### def         get_summary_as_string(self) -> str:
Create a human-readable string showcasing a summary of the content of the manager.
This includes all triggers and the amount of conditions and effects they hold.

Returns:
    The created string

### def         get_content_as_string(self) -> str:
Create a human-readable string showcasing all content of the manager.
This includes all triggers and their conditions and effects.

This is also the function that is called when doing: print(trigger_manager)

Returns:
    The created string

### def         get_trigger_as_string(	self,	trigger_select: int | AoE2ScenarioParser.objects.support.trigger_select.TriggerSelect) -> str:
Create a human-readable string showcasing trigger meta-data and content.

Args:
    trigger_select: The ID of the trigger or an object used to identify which trigger to select.

Returns:
    The created string

### def         compute_updated_display_order(self, removing_trigger_ids: List[int]):


### class     UnitManager(AoE2ScenarioParser.objects.aoe2_object.AoE2Object):
Manager of everything unit-related.

### def         create_id_generator(start_id: int) -> 'Generator[int]':
Create generator for increasing value

Args:
    start_id: The id to start returning

Returns:
    A generator which will return a +1 ID value for each time called with next.

### UnitManager(	_player_units: List[AoE2ScenarioParser.objects.data_objects.units.player_units.PlayerUnits],	next_unit_id: int,	**kwargs)

### units: List[List[AoE2ScenarioParser.objects.data_objects.unit.Unit]]

### reference_id_generator: 'Generator[int]'

### next_unit_id

### def         update_unit_player_values(self):
Function to update all player values in all units. Useful when units are moved manually (in mass).

### def         clone_unit(	self,	unit: AoE2ScenarioParser.objects.data_objects.unit.Unit,	player: int | AoE2ScenarioParser.datasets.players.PlayerId = None,	unit_const: int = None,	x: float = None,	y: float = None,	z: float = None,	rotation: float = None,	garrisoned_in_id: int = None,	capture_flag: int | AoE2ScenarioParser.datasets.trigger_lists.capture_flag.CaptureFlag = None,	animation_frame: int = None,	status: int | AoE2ScenarioParser.datasets.trigger_lists.object_state.ObjectState = None,	reference_id: int = None,	tile: Union[AoE2ScenarioParser.objects.support.tile.Tile, Tuple[int, int]] = None) -> AoE2ScenarioParser.objects.data_objects.unit.Unit:
Clones an existing unit with the adjusted variables. Everything except the initial unit is optional.
When arguments are provided, they will override the corresponding values in the cloned unit.

Args:
    unit: The unit to clone
    player: The player to set the cloned unit to (If not provided, the original player will be used)
    unit_const: The unit you're placing (If not provided, the original unit constant will be used)
    x: The X coordinate of the cloned unit (If not provided, the original x coordinate will be used)
    y: The Y coordinate of the cloned unit (If not provided, the original y coordinate will be used)
    z: The Z coordinate of the cloned unit (If not provided, the original z coordinate will be used)
    rotation: The rotation of the cloned unit (If not provided, the original rotation will be used)
    garrisoned_in_id: The id of the garrisoned unit (If not provided, the original garrisoned id will be used)
    capture_flag: The capture flag of the unit unit (If not provided, the original garrisoned id will be used)
    animation_frame: The animation frame of the cloned unit (If not provided, the original animation frame will be used)
    status: The status of the cloned unit (If not provided, the original status will be used)
    reference_id: Reference id of the cloned unit (If not provided, a new reference id will be generated)
    tile: The tile of the cloned unit (If not provided, the original x,y coordinates will be used)

Returns:
    The cloned unit

### def         add_unit(	self,	player: int | AoE2ScenarioParser.datasets.players.PlayerId,	unit_const: int,	x: float = 0,	y: float = 0,	z: float = 0,	rotation: float = 0,	garrisoned_in_id: int = -1,	animation_frame: int = 0,	status: int | AoE2ScenarioParser.datasets.trigger_lists.object_state.ObjectState = 2,	reference_id: int = None,	capture_flag: int | AoE2ScenarioParser.datasets.trigger_lists.capture_flag.CaptureFlag = <CaptureFlag.DEFAULT: -1>,	caption_string_id: int = -1,	caption_string: str = '',	tile: Union[AoE2ScenarioParser.objects.support.tile.Tile, Tuple[int, int]] = None) -> AoE2ScenarioParser.objects.data_objects.unit.Unit:
Adds a unit to the scenario.

Args:
    player: The player the unit belongs to.
    unit_const: Defines what unit you're placing. The IDs used in the unit/buildings dataset.
    x: The x location in the scenario.
    y: The y location in the scenario.
    z: The z (height) location in the scenario.
    rotation: The rotation of the unit.
    garrisoned_in_id: The reference_id of another unit this unit is garrisoned in.
    animation_frame: The animation frame of the unit.
    status: Unknown - Always 2. 0-6 no difference (?) | 7-255 makes it disappear. (Except from the mini-map)
    reference_id: The reference ID of this unit. Normally added automatically. Used for garrisoning or reference
        in triggers
    capture_flag: Capture flag
    caption_string_id: A string ID for the caption of a unit (mut. exclusive to caption_string)
    caption_string: A string for the caption of a unit (overrides, mut. exclusive to caption_string_id)
    tile: An object that represents a tile on the map. Replaces parameters x and y. Also, automatically adds
        .5 to both ints to place the unit centered on the tile.

Returns:
    The Unit created

### def         get_player_units(	self,	player: int | AoE2ScenarioParser.datasets.players.PlayerId) -> List[AoE2ScenarioParser.objects.data_objects.unit.Unit]:
Returns a list of UnitObjects for the given player.

Raises:
    ValueError: If player is not between 0 (GAIA) and 8 (EIGHT)

### def         get_all_units(self) -> List[AoE2ScenarioParser.objects.data_objects.unit.Unit]:

### def         filter_units_by(	self,	attr: str,	unit_attrs: List[int],	blacklist: bool = False,	player_list: List[Union[int, AoE2ScenarioParser.datasets.players.PlayerId]] = None,	unit_list: List[AoE2ScenarioParser.objects.data_objects.unit.Unit] = None) -> List[AoE2ScenarioParser.objects.data_objects.unit.Unit]:
Filter units based on a given attribute of units

Args:
    attr: The attribute to filter by
    unit_attrs: The values for the attributes to filter with
    blacklist: Use the given constant list as blacklist instead of whitelist
    player_list: A list of players to filter from. If not used, all players are used.
    unit_list: A set of units to filter from. If not used, all units are used.

Returns:
    A list of units

Raises:
    AttributeError: If the provided attr does not exist on objects of the Unit class

### def         filter_units_by_const(	self,	unit_consts: List[int],	blacklist: bool = False,	player_list: List[Union[int, AoE2ScenarioParser.datasets.players.PlayerId]] = None,	unit_list: List[AoE2ScenarioParser.objects.data_objects.unit.Unit] = None) -> List[AoE2ScenarioParser.objects.data_objects.unit.Unit]:
Filter unit on their unit_const value.

Args:
    unit_consts: The constants to filter with
    blacklist: Use the given constant list as blacklist instead of whitelist
    player_list: A list of players to filter from. If not used, all players are used.
    unit_list: A set of units to filter from. If not used, all units are used.

Returns:
    A list of units

### def         filter_units_by_reference_id(	self,	unit_reference_ids: List[int],	blacklist: bool = False,	player_list: List[Union[int, AoE2ScenarioParser.datasets.players.PlayerId]] = None,	unit_list: List[AoE2ScenarioParser.objects.data_objects.unit.Unit] = None) -> List[AoE2ScenarioParser.objects.data_objects.unit.Unit]:
Filter unit on their unit_const value.

Args:
    unit_reference_ids (List[int]): The reference_ids to filter with
    blacklist (bool): Use the given constant list as blacklist instead of whitelist
    player_list (List[int]): A list of players to filter from. If not used, all players are used.
    unit_list (List[Unit]): A set of units to filter from. If not used, all units are used.

Returns:
    A list of units

### def         get_units_in_area(	self,	x1: float = None,	y1: float = None,	x2: float = None,	y2: float = None,	tile1: AoE2ScenarioParser.objects.support.tile.Tile = None,	tile2: AoE2ScenarioParser.objects.support.tile.Tile = None,	unit_list: List[AoE2ScenarioParser.objects.data_objects.unit.Unit] = None,	players: List[Union[int, AoE2ScenarioParser.datasets.players.PlayerId]] = None,	ignore_players: List[AoE2ScenarioParser.datasets.players.PlayerId] = None) -> List[AoE2ScenarioParser.objects.data_objects.unit.Unit]:
Returns all units in the square with left corner (x1, y1) and right corner (x2, y2). Both corners inclusive.

Args:
    x1: The X location of the left corner
    y1: The Y location of the left corner
    x2: The X location of the right corner
    y2: The Y location of the right corner
    tile1: The x,y location of the 1st corner as Tile Object
    tile2: The x,y location of the 2nd corner as Tile Object
    unit_list: (Optional) A list of units (Defaults to all units in the map, including GAIA (Trees etc.)
    players: (Optional) A list of Players which units need to be selected from the selected area
    ignore_players: (Optional) A list of Players which units need to be ignored from the selected area

Raises:
    ValueError: if not all 4 (x1, y1, x2 and y2) are used simultaneously.
        Or if both (tile1 and tile2) are not used simultaneously.
        Or if any of the 4 (x1, y1, x2, y2) is used together with any of (tile1, tile2). Use one or the other.
        Or if players and ignore_players are used simultaneously.

### @staticmethod
Changes a unit's ownership to the given player.

Args:
    unit: The unit object which ownership will be changed
    to_player: The player that'll get ownership over the unit (using PlayerId enum)

### def         get_new_reference_id(self) -> int:
Get a new ID each time the function is called. Starting from the current highest ID.

Returns:
    The newly generated ID

### def         find_highest_reference_id(self) -> int:
Find the highest ID in the map. Searches through all units for the highest ID.

Returns:
    The highest ID in the map

### def         remove_unit(	self,	reference_id: int = None,	unit: AoE2ScenarioParser.objects.data_objects.unit.Unit = None) -> None:
Removes a unit. Please note that unit=... is a lot faster than reference_id=... due to reference_id having
to search through all units on the map. And unit has an ownership (player) attribute which is used for knowing
which list to remove the unit from.

Args:
    reference_id: The id of the unit. Note that this is NOT a unit constant (So NOT: UnitInfo.ARCHER)
    unit: The Unit object to be removed.

### def         remove_eye_candy(self) -> None:


### class     MapManager(AoE2ScenarioParser.objects.aoe2_object.AoE2Object):
Manager of everything related to the map tab

### MapManager(	_map_color_mood: str,	map_width: int,	map_height: int,	terrain: List[AoE2ScenarioParser.objects.data_objects.terrain_tile.TerrainTile],	**kwargs)

### map_color_mood: Union[str, AoE2ScenarioParser.datasets.trigger_lists.color_mood.ColorMood]

### terrain: List[AoE2ScenarioParser.objects.data_objects.terrain_tile.TerrainTile]

### map_width: int

### map_height: int

### map_size: int

### def         get_tile(	self,	x: int = None,	y: int = None,	i: int = None) -> AoE2ScenarioParser.objects.data_objects.terrain_tile.TerrainTile:
Get a tile on the map based on xy coordinates or using the index (i)

Args:
    x: The x coordinate of the wanted tile (used together with y)
    y: The y coordinate of the wanted tile (used together with x)
    i: The index of the wanted tile

Raises:
    ValueError: If parameters (x and/or y) and i are all set
    ValueError: If the index requested is outside the index range of the terrain tiles

Returns:
    The requested tile

### def         get_tile_safe(	self,	x: int = None,	y: int = None,	i: int = None) -> AoE2ScenarioParser.objects.data_objects.terrain_tile.TerrainTile | None:
Get a tile on the map based on xy coordinates or using the index (i).
If the index is outside the map, None is returned instead of an error

Args:
    x: The x coordinate of the wanted tile (used together with y)
    y: The y coordinate of the wanted tile (used together with x)
    i: The index of the wanted tile

Returns:
    The requested tile or None if it doesn't exist

### def         get_square_1d(	self,	x1: int,	y1: int,	x2: int,	y2: int) -> List[AoE2ScenarioParser.objects.data_objects.terrain_tile.TerrainTile]:
Get a square of tiles from the map

Args:
    x1: The x1 coordinate of the square
    y1: The y1 coordinate of the square
    x2: The x2 coordinate of the square
    y2: The y2 coordinate of the square

Returns:
    1D list of terrain tiles based on given coordinates

### def         get_square_2d(	self,	x1: int,	y1: int,	x2: int,	y2: int) -> List[List[AoE2ScenarioParser.objects.data_objects.terrain_tile.TerrainTile]]:
Get a square of tiles from the map

Args:
    x1: The x1 coordinate of the square
    y1: The y1 coordinate of the square
    x2: The x2 coordinate of the square
    y2: The y2 coordinate of the square

Returns:
    2D list of lists with terrain tiles based on given coordinates

### def         set_elevation(	self,	elevation: int,	x1: int,	y1: int,	x2: int | None = None,	y2: int | None = None) -> None:
Sets elevation like the in-game elevation mechanics. Can set a hill (or single point) to a certain height and
all tiles around it are adjusted accordingly.

If you find that the in-game mechanics work differently than this function please report it.

Args:
    elevation: The elevation to create at the coordinates
    x1: The x coordinate of the west corner
    y1: The y coordinate of the west corner
    x2: The x coordinate of the east corner
    y2: The y coordinate of the east corner


### class     PlayerManager(AoE2ScenarioParser.objects.aoe2_object.AoE2Object):
Manager of everything player-related.

### PlayerManager(	_player_count: int,	_tribe_names: List[str],	_string_table_player_names: List[int],	_metadata: List[AoE2ScenarioParser.objects.data_objects.player.player_meta_data.PlayerMetaData],	_lock_civilizations: List[int],	_lock_personalities: List[int],	_resources: List[AoE2ScenarioParser.objects.data_objects.player.player_resources.PlayerResources],	_ai_names: List[str],	_ai_types: List[int],	_ai_files: List[AoE2ScenarioParser.objects.data_objects.player.player_ai_file.PlayerAiFile],	_diplomacy: List[AoE2ScenarioParser.objects.data_objects.player.player_diplomacy.PlayerDiplomacy],	_allied_victories: List[int],	_starting_ages: List[int],	_base_priorities: List[int],	_pop_caps: List[int],	_initial_player_views: List[AoE2ScenarioParser.objects.data_objects.player.player_initial_view.PlayerInitialView],	_player_data_4: List[AoE2ScenarioParser.objects.data_objects.player.player_data_four.PlayerDataFour],	_player_data_3: List[AoE2ScenarioParser.objects.data_objects.player.player_data_three.PlayerDataThree],	**kwargs)

### players: List[AoE2ScenarioParser.objects.data_objects.player.player.Player]
Returns all player objects

### active_players: int
The amount of players that are active within the scenario

### def         set_default_starting_resources(	self,	players: List[AoE2ScenarioParser.datasets.players.PlayerId] = None) -> None:
Sets the default starting resources for all players

Warning: Does NOT take civilizations into account
    This does not take the current selected civ of this player into account. For example, a player with the
    Chinese civ selected will still be set to 200 food. Generally speaking, it's recommended to not use this for
    competitive, normal play. You can select low resources in the lobby menu to get 'normal' resources for
    every civ.

Args:
    players: A list of players, defaults to all players (incl GAIA) when left out

### def         set_diplomacy_teams(	self,	*args: List[Union[int, AoE2ScenarioParser.datasets.players.PlayerId]],	diplomacy: AoE2ScenarioParser.datasets.trigger_lists.diplomacy_state.DiplomacyState = <DiplomacyState.ALLY: 0>) -> None:
Sets all players in list allied with all others in the same list.

Args:
    *args: List(s) with player IDs that'll be set to the given diplomacy value
    diplomacy: The diplomacy to set the teams to. Defaults to ally.

Examples:
    To set diplomacy like a 4v4 in ranked. Two teams of 4 with alternating IDs.

    set_diplomacy_teams([1,3,5,7], [2,4,6,8], diplomacy=DiplomacyState.ALLY)


### class     OptionManager(AoE2ScenarioParser.objects.aoe2_object.AoE2Object):
Manager of all general (global) options

### OptionManager(	victory_condition: int,	victory_score: int,	_victory_years_10ths: int,	victory_custom_conditions_required: bool,	secondary_game_modes: int,	lock_teams: bool,	random_start_points: bool,	allow_players_choose_teams: bool,	collide_and_correct: bool,	villager_force_drop: bool,	lock_coop_alliances: bool,	legacy_execution_order: bool,	**kwargs)

### victory_condition: int | AoE2ScenarioParser.datasets.trigger_lists.victory_condition.VictoryCondition

### victory_score: int

### victory_custom_conditions_required: bool

### secondary_game_modes: int | AoE2ScenarioParser.datasets.trigger_lists.secondary_game_mode.SecondaryGameMode

### lock_teams: bool

### random_start_points: bool

### allow_players_choose_teams: bool

### collide_and_correct: bool

### villager_force_drop: bool

### lock_coop_alliances: bool

### legacy_execution_order

### victory_years: float


### class     XsManager(AoE2ScenarioParser.objects.aoe2_object.AoE2Object):
Manager of everything XS-related.

### XsManager(script_name: str, **kwargs)

### xs_check

### script_name
The XS script name to include in the scenario

### xs_trigger
The trigger holding the script call effect holding all the XS

### def         initialise_xs_trigger(self, insert_index: int = -1) -> None:
Creates the XS trigger on a desired location. If you don't care about the location, the add_script() function
adds the trigger when calling it the first time too.

If you want the trigger to be (almost) at the top of the list, and you're reading a scenario with barely any to
no triggers, it is recommended to call this somewhere at the start of the script.

Insert index is used to move this trigger to a desired index.
Keep in mind that moving triggers like this might take some time when you have a lot of triggers (thousands).

Args:
    insert_index: The index where the xs trigger is added. Will be added at the end of the list if left empty

### def         add_script(	self,	xs_file_path: str = '',	xs_string: str = '',	validate: bool = False):
Add a script to the script call effect in the XS trigger

Args:
    xs_file_path: Path to an XS file
    xs_string: Raw XS
    validate: If the given XS code should be validated using Alian713/xs-check → https://github.com/Divy1211/xs-check

### def         validate(self, xs: str = '', xs_path: Union[pathlib.Path, str] = '') -> True:
Validate a given string

Args:
    xs: The XS string (not file path) to validate
    xs_path: A path to an XS file

Throws:
    XsCheckValidationError: When xs-check encounters an error

Returns:
    True when the validation succeeds without errors. Throws an XsCheckValidationError otherwise

### def         validate_scenario_xs(self):


### class     MessageManager(AoE2ScenarioParser.objects.aoe2_object.AoE2Object):
Manager of everything related to the message tab

### MessageManager(	instructions: str,	hints: str,	victory: str,	loss: str,	history: str,	scouts: str,	instructions_string_table_id: int,	hints_string_table_id: int,	victory_string_table_id: int,	loss_string_table_id: int,	history_string_table_id: int,	scouts_string_table_id: int,	**kwargs)

### instructions: str

### hints: str

### victory: str

### loss: str

### history: str

### scouts: str

### instructions_string_table_id: int

### hints_string_table_id: int

### victory_string_table_id: int

### loss_string_table_id: int

### history_string_table_id: int

### scouts_string_table_id: int


---

## 数据对象


### class     Trigger(AoE2ScenarioParser.objects.aoe2_object.AoE2Object, AoE2ScenarioParser.objects.support.trigger_object.TriggerComponent):
Object for handling a trigger.

### Trigger(	name: str,	description: str = '',	description_stid: int = -1,	display_as_objective: int = 0,	short_description: str = '',	short_description_stid: int = -1,	display_on_screen: int = 0,	description_order: int = 0,	enabled: int = 1,	looping: int = 0,	execute_on_load: int = 0,	header: int = 0,	mute_objectives: int = 0,	conditions: List[AoE2ScenarioParser.objects.data_objects.condition.Condition] = None,	condition_order: List[int] = None,	effects: List[AoE2ScenarioParser.objects.data_objects.effect.Effect] = None,	effect_order: List[int] = None,	trigger_id: int = -1,	**kwargs)

### name: str

### description: str

### description_stid: int

### display_as_objective: int

### short_description: str

### short_description_stid: int

### display_on_screen: int

### description_order: int

### enabled: int

### looping: int

### execute_on_load: int

### header: int

### mute_objectives: int

### conditions: List[AoE2ScenarioParser.objects.data_objects.condition.Condition]
All conditions in this trigger

### condition_order: List[int]
The condition display order

### effects: List[AoE2ScenarioParser.objects.data_objects.effect.Effect]
All effects in this trigger

### effect_order: List[int]
The effect display order

### trigger_id: int

### new_effect: AoE2ScenarioParser.objects.support.new_effect.NewEffectSupport

### new_condition: AoE2ScenarioParser.objects.support.new_condition.NewConditionSupport

### def         get_effect(	self,	effect_index: int = None,	display_index: int = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:
Retrieve an effect based on its (display) index

Args:
    effect_index: The effect index of the effect to retrieve
    display_index: The display index of the effect to retrieve

Raises:
    ValueError: If more than one parameter is used simultaneously
    IndexError: If the effect could not be found

Returns:
    The wanted effect

### def         get_condition(	self,	condition_index: int = None,	display_index: int = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:
Retrieve a condition based on its (display) index

Args:
    condition_index: The condition index of the condition to retrieve
    display_index: The display index of the condition to retrieve

Raises:
    ValueError: If more than one parameter is used simultaneously
    IndexError: If the condition could not be found

Returns:
    The wanted condition

### def         remove_effect(	self,	effect_index: int = None,	display_index: int = None,	effect: AoE2ScenarioParser.objects.data_objects.effect.Effect = None) -> None:
Remove an effect from this trigger

Args:
    effect_index: The effect index of the condition to remove
    display_index: The display index of the condition to remove
    effect: A reference to the effect object to remove from this trigger

Raises:
    ValueError: If more than one parameter is used simultaneously

### def         remove_condition(	self,	condition_index: int = None,	display_index: int = None,	condition: AoE2ScenarioParser.objects.data_objects.condition.Condition = None) -> None:
Remove a condition from this trigger

Args:
    condition_index: The condition index of the condition to remove
    display_index: The display index of the condition to remove
    condition: A reference to the condition object to remove from this trigger

Raises:
    ValueError: If more than one parameter is used simultaneously

### def         get_content_as_string(self, include_trigger_definition: bool = False) -> str:
Create a human-readable string showcasing all content of this trigger.
This includes all the content within the conditions and effects of this trigger.

This is also the function that is called when doing: print(trigger)

Args:
    include_trigger_definition: If the trigger meta-data should be added by this function

Returns:
    The created string


### class     Effect(AoE2ScenarioParser.objects.aoe2_object.AoE2Object, AoE2ScenarioParser.objects.support.trigger_object.TriggerComponent):
Object for handling an effect.

### Effect(	effect_type: int = None,	ai_script_goal: int = None,	armour_attack_quantity: int = None,	armour_attack_class: int = None,	_quantity_int: int = None,	tribute_list: int = None,	diplomacy: int = None,	legacy_location_object_reference: int = None,	object_list_unit_id: int = None,	source_player: int = None,	target_player: int = None,	technology: int = None,	string_id: int = None,	display_time: int = None,	trigger_id: int = None,	location_x: int = None,	location_y: int = None,	location_object_reference: int = None,	area_x1: int = None,	area_y1: int = None,	area_x2: int = None,	area_y2: int = None,	object_group: int = None,	object_type: int = None,	instruction_panel_position: int = None,	attack_stance: int = None,	time_unit: int = None,	enabled: int = None,	food: int = None,	wood: int = None,	stone: int = None,	gold: int = None,	item_id: int = None,	flash_object: int = None,	force_research_technology: int = None,	visibility_state: int = None,	scroll: int = None,	operation: int = None,	object_list_unit_id_2: int = None,	button_location: int = None,	ai_signal_value: int = None,	object_attributes: int = None,	variable: int = None,	timer: int = None,	facet: int = None,	play_sound: int = None,	player_color: int = None,	color_mood: int = None,	reset_timer: int = None,	object_state: int = None,	action_type: int = None,	resource_1: int = None,	resource_1_quantity: int = None,	resource_2: int = None,	resource_2_quantity: int = None,	resource_3: int = None,	resource_3_quantity: int = None,	decision_id: int = None,	string_id_option1: int = None,	string_id_option2: int = None,	variable2: int = None,	max_units_affected: int = None,	disable_garrison_unload_sound: int = None,	hotkey: int = None,	train_time: int = None,	local_technology: int = None,	disable_sound: int = None,	object_group2: int = None,	object_type2: int = None,	_quantity_float: float = None,	facet2: int = None,	global_sound: int = None,	issue_group_command: int = None,	queue_action: int = None,	mutual_diplomacy: int = None,	building_list: int = None,	wall_x1: int = None,	wall_y1: int = None,	wall_x2: int = None,	wall_y2: int = None,	object_filter: int = None,	use_tag_color_for_icon: bool = None,	message: str = None,	sound_name: str = None,	selected_object_ids: List[int] = None,	message_option1: str = None,	message_option2: str = None,	_variable_ref: int = None,	quantity: int = None,	**kwargs)

### hidden_attribute        = 'effect_type'
The attribute that should not be shown in this component. Used to hide the identifier in printing jobs

### ai_script_goal: int

### armour_attack_quantity
Helper property for handling the armour_attack related values

### armour_attack_class
Helper property for handling the armour_attack related values

### quantity: int
Getter for quantity, even if it is combined with armour_attack_quantity and armour_attack_class

### tribute_list: int

### diplomacy: int

### object_list_unit_id: int

### source_player: int

### target_player: int

### technology: int

### string_id: int

### display_time: int

### trigger_id: int

### location_x: int

### location_y: int

### location_object_reference: int

### area_x1: int

### area_y1: int

### area_x2: int

### area_y2: int

### object_group: int

### object_type: int

### instruction_panel_position: int

### attack_stance: int

### time_unit: int

### enabled: int

### food: int

### wood: int

### stone: int

### gold: int

### flash_object: int

### force_research_technology: int

### visibility_state: int

### scroll: int

### operation: int

### object_list_unit_id_2: int

### button_location: int

### ai_signal_value: int

### object_attributes

### variable: int

### timer: int

### facet: int

### play_sound: int

### player_color
Get the player color attribute

### color_mood: int

### reset_timer: int

### object_state: int

### action_type: int

### resource_1: int

### resource_1_quantity: int

### resource_2: int

### resource_2_quantity: int

### resource_3: int

### resource_3_quantity: int

### decision_id: int

### string_id_option1: int

### string_id_option2: int

### variable2: int

### max_units_affected: int

### disable_garrison_unload_sound: int

### hotkey: int

### train_time: int

### local_technology: int

### disable_sound: int

### object_group2: int

### object_type2: int

### facet2: int

### global_sound: int

### issue_group_command: int

### queue_action: int

### mutual_diplomacy: int

### building_list: int

### wall_x1: int

### wall_y1: int

### wall_x2: int

### wall_y2: int

### object_filter: int

### use_tag_color_for_icon: bool

### message: str

### sound_name: str

### selected_object_ids: List[int]
Get the current selected objects

### message_option1: str

### message_option2: str

### legacy_location_object_reference: int
Getter for legacy object_reference location. Always returns -1.

### item_id
Get the currently selected item_id based on other attributes

### effect_type
The type of the effect (EffectId dataset)

### def         get_content_as_string(self, include_effect_definition: bool = False) -> str:
Create a human-readable string showcasing all content of this effect.

This is also the function called when doing: print(effect)

Args:
    include_effect_definition: If the effect meta-data should be added to the result

Returns:
    The created string


### class     Condition(AoE2ScenarioParser.objects.aoe2_object.AoE2Object, AoE2ScenarioParser.objects.support.trigger_object.TriggerComponent):
Object for handling a condition.

### Condition(	condition_type: int = None,	quantity: int = None,	attribute: int = None,	unit_object: int = None,	next_object: int = None,	object_list: int = None,	source_player: int | enum.IntEnum = None,	technology: int | enum.IntEnum = None,	timer: int = None,	trigger_id: int = None,	area_x1: int = None,	area_y1: int = None,	area_x2: int = None,	area_y2: int = None,	object_group: int = None,	object_type: int = None,	ai_signal: int = None,	inverted: int = None,	variable: int = None,	comparison: int = None,	target_player: int | enum.IntEnum = None,	unit_ai_action: int = None,	object_state: int = None,	timer_id: int = None,	victory_timer_type: int = None,	include_changeable_weapon_objects: int = None,	decision_id: int = None,	decision_option: int = None,	variable2: int = None,	local_technology: int = None,	object_group2: int = None,	object_type2: int = None,	allow_in_fog: int = None,	xs_function: str = None,	**kwargs)

### hidden_attribute        = 'condition_type'
The attribute that should not be shown in this component. Used to hide the identifier in printing jobs

### condition_type: int

### quantity: int

### attribute: int

### unit_object: int

### next_object: int

### object_list: int

### source_player: int

### technology: int

### timer: int

### trigger_id: int

### area_x1: int

### area_y1: int

### area_x2: int

### area_y2: int

### object_group: int

### object_type: int

### ai_signal: int

### inverted: int

### variable: int

### comparison: int

### target_player: int

### unit_ai_action: int

### object_state: int

### timer_id: int

### victory_timer_type: int

### include_changeable_weapon_objects: int

### decision_id: int

### decision_option: int

### variable2: int

### local_technology: int

### object_group2: int

### object_type2: int

### allow_in_fog: int

### xs_function: str

### def         get_content_as_string(self, include_condition_definition: bool = False) -> str:
Create a human-readable string showcasing all content of this condition.

This is also the function that is called when doing: print(condition)

Args:
    include_condition_definition: If the condition meta-data should be added by this function

Returns:
    The created string


### class     Variable(AoE2ScenarioParser.objects.aoe2_object.AoE2Object):
Object for handling a variable.

### Variable(variable_id: int, name: str, **kwargs)

### variable_id

### name


### class     Unit(AoE2ScenarioParser.objects.aoe2_object.AoE2Object):
A class representing a single unit on the map.
This can be an archer, a gold mine, a house or even a tree.

### Unit(	player: int | AoE2ScenarioParser.datasets.players.PlayerId,	x: float,	y: float,	z: float,	reference_id: int,	unit_const: int,	status: int | AoE2ScenarioParser.datasets.trigger_lists.object_state.ObjectState,	rotation: float,	initial_animation_frame: int,	garrisoned_in_id: int = -1,	capture_flag: int | AoE2ScenarioParser.datasets.trigger_lists.capture_flag.CaptureFlag = -1,	caption_string_id: int = -1,	caption_string: str = '',	**kwargs)

### x: float

### y: float

### z: float

### reference_id: int

### unit_const: int

### status: int | AoE2ScenarioParser.datasets.trigger_lists.object_state.ObjectState

### rotation: float

### initial_animation_frame: int

### garrisoned_in_id: int

### capture_flag: int | AoE2ScenarioParser.datasets.trigger_lists.capture_flag.CaptureFlag

### caption_string_id: int

### caption_string: str

### player: AoE2ScenarioParser.datasets.players.PlayerId
The player that owns this unit

### tile: AoE2ScenarioParser.objects.support.tile.Tile
The tile where the unit is located

### name: str
The name of the unit, nicely formatted


### class     TerrainTile(AoE2ScenarioParser.objects.aoe2_object.AoE2Object):
The X coordinate of this tile on the map

### TerrainTile(	terrain_id: int = <TerrainId.GRASS_1: 0>,	elevation: int = 0,	layer: int = -1,	_index: int = -1,	**kwargs)

### terrain_id: int

### elevation: int

### layer: int

### x: int
The X coordinate of this tile on the map

### y: int
The Y coordinate of this tile on the map

### i: int
The index of this tile on the map

### xy: Tuple[int, int]
The X,Y coordinate of this tile on the map

Returns:
    A tuple containing two integers representing the XY coordinates


### class     Player(AoE2ScenarioParser.objects.aoe2_object.AoE2Object):
A class for handling all player information.

### Player(	player_id: int,	starting_age: int,	lock_civ: int,	lock_personality: int,	food: int,	wood: int,	gold: int,	stone: int,	personality: str,	ai_type: int,	ai_script: str,	color: int,	active: bool,	human: bool,	civilization: int,	architecture_set: int,	population_cap: Optional[int] = None,	diplomacy: Optional[List[int]] = None,	initial_camera_x: Optional[int] = None,	initial_camera_y: Optional[int] = None,	allied_victory: Optional[int] = None,	disabled_techs: Optional[List[int]] = None,	disabled_buildings: Optional[List[int]] = None,	disabled_units: Optional[List[int]] = None,	tribe_name: Optional[str] = None,	base_priority: Optional[int] = None,	string_table_name_id: Optional[int] = None,	initial_player_view_x: Optional[int] = None,	initial_player_view_y: Optional[int] = None,	**kwargs)

### starting_age: int

### lock_civ: bool

### lock_personality: bool

### food: int

### wood: int

### gold: int

### stone: int

### personality: str

### ai_type: int | AoE2ScenarioParser.datasets.players.AiType

### ai_script: str

### color: int

### human: bool

### civilization: AoE2ScenarioParser.datasets.object_support.Civilization | str | int

### architecture_set: AoE2ScenarioParser.datasets.object_support.Civilization | str | int

### population_cap: Optional[int]

### diplomacy: Optional[List[int]]

### allied_victory: Optional[bool]

### disabled_techs: Optional[List[int]]

### disabled_buildings: Optional[List[int]]

### disabled_units: Optional[List[int]]

### tribe_name: Optional[str]

### base_priority: Optional[int]

### string_table_name_id: Optional[int]

### initial_player_view_x: Optional[int]

### initial_player_view_y: Optional[int]

### initial_camera_x

### initial_camera_y

### player_id: int
Read-only value of the player ID

### active: bool
Read-only value if this player is active or not

### def         set_none_ai(self):
Sets the personality of this player to None AI

### def         set_immobile_ai(self):
Sets the personality of this player to an immobile AI

### def         set_custom_ai(	self,	name: str,	ai_script: str | None = None,	per_file_path: str | None = None):
Sets the personality of this player to your custom AI

### def         set_player_diplomacy(	self,	players: Union[AoE2ScenarioParser.datasets.players.PlayerId, int, List[Union[int, AoE2ScenarioParser.datasets.players.PlayerId]]],	diplomacy: AoE2ScenarioParser.datasets.trigger_lists.diplomacy_state.DiplomacyState):
Set the diplomacy of this player to other players.

Note: This sets the player diplomacy ONE WAY!
    This does NOT set the other player's diplomacy to this player to the same diplomacy

Args:
    players: The player(s) to change
    diplomacy: The diplomacy setting to set the player to

### @staticmethod


---

## 支持对象


### class     AreaState(enum.Enum):
Enum to show the state of the Area object

### class     AreaAttr(enum.Enum):
Enum to show the supported attributes that can be edited using Area.attr(k, v)

### class     Area:
Object to easily select an area on the map. Uses method chaining for ease of use.

Please note: Setting a uuid will always overwrite the map_size attribute, even if it's not None.

Args:
    map_size: The size of the map this area object will handle
    uuid: The UUID of the scenario this area belongs to
    x1: The X location of the left corner
    y1: The Y location of the left corner
    x2: The X location of the right corner
    y2: The Y location of the right corner
    corner1: The location of the left corner
    corner2: The location of the right corner

### FULL        = <AreaState.FULL: 0>

### EDGE        = <AreaState.EDGE: 1>

### GRID        = <AreaState.GRID: 2>

### LINES        = <AreaState.LINES: 3>

### CORNERS        = <AreaState.CORNERS: 4>

### @staticmethod
Returns the states that cannot be split into chunks

### X1        = <AreaAttr.X1: 'x1'>

### Y1        = <AreaAttr.Y1: 'y1'>

### X2        = <AreaAttr.X2: 'x2'>

### Y2        = <AreaAttr.Y2: 'y2'>

### GAP_SIZE        = <AreaAttr.GAP_SIZE: 'gap_size'>

### GAP_SIZE_X        = <AreaAttr.GAP_SIZE_X: 'gap_size_x'>

### GAP_SIZE_Y        = <AreaAttr.GAP_SIZE_Y: 'gap_size_y'>

### LINE_WIDTH        = <AreaAttr.LINE_WIDTH: 'line_width'>

### LINE_WIDTH_X        = <AreaAttr.LINE_WIDTH_X: 'line_width_x'>

### LINE_WIDTH_Y        = <AreaAttr.LINE_WIDTH_Y: 'line_width_y'>

### AXIS        = <AreaAttr.AXIS: 'axis'>

### CORNER_SIZE        = <AreaAttr.CORNER_SIZE: 'corner_size'>

### CORNER_SIZE_X        = <AreaAttr.CORNER_SIZE_X: 'corner_size_x'>

### CORNER_SIZE_Y        = <AreaAttr.CORNER_SIZE_Y: 'corner_size_y'>

### BLOCK_SIZE        = <AreaAttr.BLOCK_SIZE: 'block_size'>

### BLOCK_SIZE_X        = <AreaAttr.BLOCK_SIZE_X: 'block_size_x'>

### BLOCK_SIZE_Y        = <AreaAttr.BLOCK_SIZE_Y: 'block_size_y'>

### Area(	map_size: int = None,	uuid: uuid.UUID = None,	x1: int = None,	y1: int = None,	x2: int = None,	y2: int = None,	corner1: AoE2ScenarioParser.objects.support.tile.Tile = None,	corner2: AoE2ScenarioParser.objects.support.tile.Tile = None)
Object to easily select an area on the map. Uses method chaining for ease of use.

Please note: Setting a uuid will always overwrite the map_size attribute, even if it's not None.

Args:
    map_size: The size of the map this area object will handle
    uuid: The UUID of the scenario this area belongs to
    x1: The X location of the left corner
    y1: The Y location of the left corner
    x2: The X location of the right corner
    y2: The Y location of the right corner
    corner1: The location of the left corner
    corner2: The location of the right corner

### uuid: uuid.UUID

### state: AreaState

### inverted: bool

### x1: int

### y1: int

### x2: int

### y2: int

### gap_size_x: int

### gap_size_y: int

### line_width_x: int

### line_width_y: int

### block_size_x: int

### block_size_y: int

### axis: str

### corner_size_x: int

### corner_size_y: int

### @classmethod

### @classmethod

### corner1

### corner2

### map_size

### maximum_coordinate: int
The maximum coordinate for the X or Y axis (like how 0 is the minimum)

### def         associate_scenario(	self,	scenario: AoE2ScenarioParser.scenarios.aoe2_scenario.AoE2Scenario) -> None:
Associate area with scenario. Saves scenario UUID in this area object.

Args:
    scenario: The scenario to associate with

### def         to_coords(self, as_terrain: bool = False) -> "OrderedSet[Tile | 'TerrainTile']":
Converts the selection to an OrderedSet of (x, y) coordinates

Args:
    as_terrain: If the returning coordinates should be Tile objects or Terrain Tiles. If True the coordinates
        are returned as TerrainTiles.

Returns:
    An OrderedSet of Tiles ((x, y) named tuple) of the selection.

Examples:
    The selection: ((3,3), (5,5)) would result in an OrderedSet with a length of 9::

    [
        (3,3), (4,3)  ...,
        ...,   ...,   ...,
        ...,   (4,5), (5,5)
    ]

### def         to_chunks(	self,	as_terrain: bool = False) -> "List[OrderedSet[Tile | 'TerrainTile']]":
Converts the selection to a list of OrderedSets with Tile NamedTuples with (x, y) coordinates.
The separation between chunks is based on if they're connected to each other.
So the tiles must share an edge (i.e. they should be non-diagonal).
(With exceptions like grid state when using gap_size = 0)

Args:
    as_terrain: If the returning coordinates should be Tile objects or Terrain Tiles. If True the coordinates
        are returned as TerrainTiles.

Returns:
    A list of OrderedSets with Tiles ((x, y) named tuple) of the selection.

### def         to_chunk_areas(self) -> List[Area]:
Converts the selection to a list of Area objects.
Internally, this uses to_chunks to convert the selection to chunks.
The separation between chunks is based on if they're connected to each other.
So the tiles must share an edge (i.e. they should be non-diagonal).
(With exceptions like grid state when using gap_size = 0)

Returns:
    A list with Area objects based on the selection.

### def         to_dict(self, prefix: str = 'area_') -> Dict[str, int]:
Converts the 2 corners of the selection to area keys for use in effects etc.
This can be used by adding double stars (**) before this function.

Usage:
    The selection: ((3,3), (5,5)) would result in a dict that looks like:
        {'area_x1': 3, 'area_y1': 3, 'area_x2': 5, 'area_y2': 5}
    Then do: **area.to_dict() in a function that accepts area tiles

Args:
    prefix: The prefix of the string before 'x1' (e.g. prefix="coord_" will result in: "coord_x1" as key)

Returns:
    A dict with area_x1, area_y1, area_x2, area_y2 as keys and their respective values (if prefix is unchanged).

### def         get_selection(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
Get the four values of the selection as: ((x1, y1), (x2, y2))

### def         get_raw_selection(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
Get the four values of the selection (even if they are outside the map) as: ((x1, y1), (x2, y2))

### def         get_center(self) -> Tuple[float, float]:
Get center of current selection

### def         get_center_int(self) -> Tuple[int, int]:
Get center of current selection, coords can only be integers. If even length, the value is ceiled

### def         get_range_x(self) -> range:
Returns a range object for the x coordinates.

### def         get_range_y(self) -> range:
Returns a range object for the y coordinates.

### def         get_width(self) -> int:
Returns the length of the x side of the selection.

### def         get_height(self) -> int:
Returns the length of the y side of the selection.

### def         get_dimensions(self) -> Tuple[int, int]:
Returns the lengths of the x & y side of the selection (in that order).

### def         use_full(self) -> Area:
Sets the area object to use the entire selection

### def         use_only_edge(	self,	line_width: int = None,	line_width_x: int = None,	line_width_y: int = None) -> Area:
Sets the area object to only use the edge of the selection

Args:
    line_width: The width of the x & y edge line
    line_width_x: The width of the x edge line
    line_width_y: The width of the y edge line

Returns:
    This area object

### def         use_only_corners(	self,	corner_size: int = None,	corner_size_x: int = None,	corner_size_y: int = None) -> Area:
Sets the area object to only use the corners pattern within the selection.

Args:
    corner_size: The size along both the x and y-axis of the corner areas
    corner_size_x: The size along the x-axis of the corner areas
    corner_size_y: The size along the y-axis of the corner areas

Returns:
    This area object

### def         use_pattern_grid(	self,	block_size: int = None,	gap_size: int = None,	block_size_x: int = None,	block_size_y: int = None,	gap_size_x: int = None,	gap_size_y: int = None) -> Area:
Sets the area object to use a grid pattern within the selection.

Args:
    block_size: The size of the gaps between lines
    gap_size: The width of the grid lines
    block_size_x: The size of the x gaps between lines
    block_size_y: The size of the y gaps between lines
    gap_size_x: The width of the x grid lines
    gap_size_y: The width of the y grid lines

Returns:
    This area object

### def         use_pattern_lines(	self,	axis: str = None,	gap_size: int = None,	line_width: int = None) -> Area:
Sets the area object to use a lines pattern within the selection.

Args:
    axis: The axis the lines should follow. Can either be "x" or "y"
    gap_size: The size of the gaps between lines
    line_width: The width of the x & y lines

Returns:
    This area object

### def         invert(self) -> Area:
Inverts the inverted boolean. Causes the to_coords to return the inverted selection. This function is
especially useful for the grid state. It's not as useful for the edge which would be the same as shrinking the
selection. When used with the fill state an empty set is returned.

Please note: This inverts the INTERNAL selection. Tiles OUTSIDE the selection will NOT be returned.

### def         along_axis(self, axis: str) -> Area:
Sets the axis. Can be either "x" or "y".

### def         attr(	self,	key: str | AreaAttr,	value: int) -> Area:
Sets the attribute to the given value. AreaAttr or str can be used as key

### def         attrs(	self,	x1: int = None,	y1: int = None,	x2: int = None,	y2: int = None,	gap_size: int = None,	gap_size_x: int = None,	gap_size_y: int = None,	line_width: int = None,	line_width_x: int = None,	line_width_y: int = None,	axis: str = None,	corner_size: int = None,	corner_size_x: int = None,	corner_size_y: int = None,	block_size: int = None,	block_size_x: int = None,	block_size_y: int = None) -> Area:
Sets multiple attributes to the corresponding values.

Returns:
    This area object

### def         move(self, offset_x: int = 0, offset_y: int = 0):
Moves the selection area in a given direction relative to its current position

### def         move_to(	self,	corner: Literal['west', 'north', 'east', 'south'],	x: int,	y: int):
Moves the selection area to the given coordinate by placing the given corner of this area on the coordinate.

For center placement, use .center(...)

### def         size(	self,	n: int,	anchor: Optional[Literal['west', 'north', 'east', 'south']] = None) -> Area:
Sets the selection to a size of n by n.

Without an anchor, the selection is sized around the center. If center is (4,4) with a size of 3 the selection
will become ((3,3), (5,5))

With an anchor, that corner stays in place and only the opposite sides move. If the expansion hits the edge of
the map, it's clamped, so the resulting size can be smaller than n.

Args:
    n: The new width and height
    anchor: The corner which should stay in place ('west', 'north', 'east' or 'south')

### def         height(	self,	n: int,	anchor: Optional[Literal['y1', 'y2']] = None) -> Area:
Sets the height (y-axis) of the selection.

Without an anchor, both sides shrink/expand equally. If the expansion hits the edge of the map, it'll expand
on the other side.

With an anchor, that side stays in place and only the other side moves. If the expansion hits the edge of
the map, it's clamped, so the resulting height can be smaller than n.

Args:
    n: The new height
    anchor: The side which should stay in place ('y1' or 'y2')

### def         width(	self,	n: int,	anchor: Optional[Literal['x1', 'x2']] = None) -> Area:
Sets the width (x-axis) of the selection.

Without an anchor, both sides shrink/expand equally. If the expansion hits the edge of the map, it'll expand
on the other side.

With an anchor, that side stays in place and only the other side moves. If the expansion hits the edge of
the map, it's clamped, so the resulting width can be smaller than n.

Args:
    n: The new width
    anchor: The side which should stay in place ('x1' or 'x2')

### def         center(self, x: int, y: int) -> Area:
Moves the selection center to a given position. When the given center forces the selection of the edge of the
map the off-map tiles will not be returned. When moving the selection back into the map the tiles will be
returned again.

If you want to limit moving the center without changing the selection box size, use: center_bounded

### def         center_bounded(self, x: int, y: int) -> Area:
Moves the selection center to a given position on the map. This function makes sure it cannot go over the edge
of the map. The selection will be forced against the edge of the map and the selection will not be decreased in
size.

### def         select_entire_map(self) -> Area:
Sets the selection to the entire map

### def         select(	self,	x1: int,	y1: int,	x2: int = None,	y2: int = None) -> Area:
Sets the selection to the given coordinates.
Negative coordinates are resolved from the end of the map, so -1 is the last tile on that axis.

### def         select_raw(	self,	x1: int,	y1: int,	x2: int = None,	y2: int = None) -> Area:
Sets the selection to the given coordinates without resolving negative coordinates.
A value of -1 is considered unset (like in effects and conditions), so an unset x2/y2 falls back to
x1/y1. Other negative coordinates are kept and considered off-map.

### def         select_centered(	self,	x: int,	y: int,	dx: int = 1,	dy: int = 1) -> Area:
Sets the selection to the given coordinates

### def         shrink(self, n: int) -> Area:
Shrinks the selection from all sides

### def         shrink_x1(self, n: int) -> Area:
Shrinks the selection from the first corner on the X axis by n

### def         shrink_y1(self, n: int) -> Area:
Shrinks the selection from the first corner on the Y axis by n

### def         shrink_x2(self, n: int) -> Area:
Shrinks the selection from the second corner on the X axis by n

### def         shrink_y2(self, n: int) -> Area:
Shrinks the selection from the second corner on the Y axis by n

### def         expand(self, n: int) -> Area:
Expands the selection from all sides

### def         expand_x1(self, n: int) -> Area:
Expands the selection from the first corner on the X axis by n

### def         expand_y1(self, n: int) -> Area:
Expands the selection from the first corner on the Y axis by n

### def         expand_x2(self, n: int) -> Area:
Expands the selection from the second corner on the X axis by n

### def         expand_y2(self, n: int) -> Area:
Expands the selection from the second corner on the Y axis by n

### def         is_within_selection(	self,	x: int = -1,	y: int = -1,	tile: AoE2ScenarioParser.objects.support.tile.Tile = None) -> bool:
If a given (x,y) location is within the selection.

Args:
    x: The X coordinate
    y: The Y coordinate
    tile: A Tile object, replacing the x & y coordinates

Returns:
    True if (x,y) is within the selection, False otherwise

### def         is_within_bounds(self) -> bool:
Check if the current selection is within the map

### def         copy(self) -> Area:
Copy this instance of an Area. Useful for when you want to do multiple extractions (to_...) from the same source
with small tweaks.

Examples:

Get a grid and the surrounding edge::

    area = Area.select(10,10,20,20)
    edge = area.copy().expand(1).use_only_edge().to_coords()
    # Without copy you'd have to undo all changes above. In this case that'd be: `.shrink(1)`
    grid = area.use_pattern_grid().to_coords()

Returns:
    A copy of this Area object


### class     Tile(typing.NamedTuple):
NamedTuple for tiles. use tile.x or tile.y for coord access

### Tile(x: int, y: int)
Create new instance of Tile(x, y)

### x: int
Alias for field number 0

### y: int
Alias for field number 1

### def         to_dict(self, prefix: str = 'location_') -> Dict[str, int]:
Converts the coordinates of the tile to keys for use in effects etc.
This can be used by adding double stars (**) before this function.

Usage:
    The coordinate: (4, 6) would result in a dict that looks like:
        {'location_x': 4, 'location_y': 6}
    Then do: **tile.to_dict() in a function that accepts tiles

Args:
    prefix: The prefix of the string before 'x' (e.g. prefix="coord_" will result in: "coord_x" as key)

Returns:
    A dict with location_x, location_y as keys and their respective values (if prefix is unchanged).


### class     TriggerSelect:
Object used to select a trigger in many trigger related functions. For ease of use, the alias TS can be
called. You can also use those in combination with the class methods (factory methods). Like so:

Tip: Selecting a trigger by its ID doesn't require this object
    Most functions allow you to just input 4 into the trigger_select parameter (instead of: TS.index(4))

Examples:
    TS.index(4)  To select the trigger with index 4

`TS.display(4)`  Trigger with display index 4

`TS.trigger(trigger)`  Well... The trigger object given...

### TS: Type[TriggerSelect]        = <class 'TriggerSelect'>
Alias for TriggerSelect

### TriggerSelect(	trigger_index: int = None,	display_index: int = None,	trigger: AoE2ScenarioParser.objects.data_objects.trigger.Trigger = None)
Args:
    trigger_index: The index of the trigger. Starting from 0, based on creation time
    display_index: The display index of a trigger. Starting from 0, based on display order in the editor
    trigger: The trigger object itself.

### @classmethod

### display_index

### trigger_index

### @classmethod

### @classmethod


### class     TriggerCELock:
Object used to identify which conditions and effects should be locked from change

### TriggerCELock(	lock_conditions: bool = False,	lock_effects: bool = False,	lock_condition_type: Optional[List[int]] = None,	lock_effect_type: Optional[List[int]] = None,	lock_condition_ids: Optional[List[int]] = None,	lock_effect_ids: Optional[List[int]] = None)
Args:
    lock_conditions: Lock all conditions
    lock_effects: Lock all effects
    lock_condition_type: Lock certain condition types. Example: ConditionId.OWN_OBJECTS
    lock_effect_type: Lock certain effect types. Example: EffectId.CREATE_OBJECT
    lock_condition_ids: Lock certain conditions by their id
    lock_effect_ids: Lock certain effects by their id

### lock_conditions

### lock_effects

### lock_condition_type

### lock_effect_type

### lock_condition_ids

### lock_effect_ids


### class     NewEffectSupport:
The parameters 'armour_attack_quantity' and 'armour_attack_class' are only used when object_attributes is Armor
or Attack (8 or 9). Use, 'quantity' otherwise.

### NewEffectSupport(trigger_ref)

### def         none(self) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_diplomacy(	self,	diplomacy: int | None = None,	source_player: int | None = None,	target_player: int | None = None,	mutual_diplomacy: bool | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         research_technology(	self,	source_player: int | None = None,	technology: int | None = None,	force_research_technology: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         send_chat(	self,	source_player: int | None = None,	string_id: int | None = None,	message: str | None = None,	sound_name: str | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         play_sound(	self,	source_player: int | None = None,	location_x: int | None = None,	location_y: int | None = None,	location_object_reference: int | None = None,	global_sound: int | None = None,	sound_name: str | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         tribute(	self,	quantity: int | None = None,	tribute_list: int | None = None,	source_player: int | None = None,	target_player: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         unlock_gate(	self,	selected_object_ids: Union[int, List[int], NoneType] = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         lock_gate(	self,	selected_object_ids: Union[int, List[int], NoneType] = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         activate_trigger(	self,	trigger_id: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         deactivate_trigger(	self,	trigger_id: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         ai_script_goal(	self,	ai_script_goal: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         create_object(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	location_x: int | None = None,	location_y: int | None = None,	facet: int | None = None,	disable_sound: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         task_object(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	location_x: int | None = None,	location_y: int | None = None,	location_object_reference: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	action_type: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	disable_garrison_unload_sound: int | None = None,	max_units_affected: int | None = None,	issue_group_command: int | None = None,	queue_action: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         declare_victory(	self,	source_player: int | None = None,	enabled: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         kill_object(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         remove_object(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	object_state: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_view(	self,	quantity: int | None = None,	source_player: int | None = None,	location_x: int | None = None,	location_y: int | None = None,	scroll: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         unload(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	location_x: int | None = None,	location_y: int | None = None,	location_object_reference: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_ownership(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	target_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	flash_object: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         patrol(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	location_x: int | None = None,	location_y: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         display_instructions(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	string_id: int | None = None,	display_time: int | None = None,	instruction_panel_position: int | None = None,	play_sound: int | None = None,	message: str | None = None,	sound_name: str | None = None,	use_tag_color_for_icon: bool | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         clear_instructions(	self,	instruction_panel_position: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         freeze_object(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         use_advanced_buttons(self) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         damage_object(	self,	quantity: int | None = None,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         place_foundation(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	location_x: int | None = None,	location_y: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_object_name(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	string_id: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	message: str | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: str | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_object_hp(	self,	quantity: int | None = None,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	operation: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_object_attack(	self,	armour_attack_quantity: int | None = None,	armour_attack_class: int | None = None,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	operation: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         stop_object(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         attack_move(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	location_x: int | None = None,	location_y: int | None = None,	location_object_reference: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_object_armor(	self,	armour_attack_quantity: int | None = None,	armour_attack_class: int | None = None,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	operation: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_object_range(	self,	quantity: int | None = None,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	operation: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_object_speed(	self,	quantity: int | None = None,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         heal_object(	self,	quantity: int | None = None,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         teleport_object(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	location_x: int | None = None,	location_y: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_object_stance(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	attack_stance: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         display_timer(	self,	string_id: int | None = None,	display_time: int | None = None,	time_unit: int | None = None,	timer: int | None = None,	reset_timer: int | None = None,	message: str | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         enable_disable_object(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	enabled: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         enable_disable_technology(	self,	source_player: int | None = None,	technology: int | None = None,	enabled: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_object_cost(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	resource_1: int | None = None,	resource_1_quantity: int | None = None,	resource_2: int | None = None,	resource_2_quantity: int | None = None,	resource_3: int | None = None,	resource_3_quantity: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         set_player_visibility(	self,	source_player: int | None = None,	target_player: int | None = None,	visibility_state: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_object_icon(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	object_list_unit_id_2: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         replace_object(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	target_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	object_list_unit_id_2: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	facet2: int | None = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_object_description(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	string_id: int | None = None,	message: str | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_player_name(	self,	source_player: int | None = None,	string_id: int | None = None,	message: str | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_train_location(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	object_list_unit_id_2: int | None = None,	button_location: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### @deprecated('Use `change_technology_location` instead')

### def         change_technology_location(	self,	source_player: int | None = None,	technology: int | None = None,	object_list_unit_id_2: int | None = None,	button_location: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_civilization_name(	self,	source_player: int | None = None,	string_id: int | None = None,	message: str | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         create_garrisoned_object(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_list_unit_id_2: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None,	disable_sound: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         acknowledge_ai_signal(	self,	ai_signal_value: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         modify_attribute(	self,	quantity: int | None = None,	armour_attack_quantity: int | None = None,	armour_attack_class: int | None = None,	object_list_unit_id: int | None = None,	source_player: int | None = None,	operation: int | None = None,	object_attributes: int | None = None,	message: str | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:
The parameters 'armour_attack_quantity' and 'armour_attack_class' are only used when object_attributes is Armor
or Attack (8 or 9). Use, 'quantity' otherwise.

### def         modify_resource(	self,	quantity: int | None = None,	tribute_list: int | None = None,	source_player: int | None = None,	operation: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         modify_resource_by_variable(	self,	tribute_list: int | None = None,	source_player: int | None = None,	operation: int | None = None,	variable: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         set_building_gather_point(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	location_x: int | None = None,	location_y: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         script_call(	self,	string_id: int | None = None,	message: str | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_variable(	self,	quantity: int | None = None,	operation: int | None = None,	variable: int | None = None,	message: str | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         clear_timer(	self,	timer: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_object_player_color(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	player_color: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_object_civilization_name(	self,	source_player: int | None = None,	string_id: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	message: str | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_object_player_name(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	string_id: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	message: str | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         disable_unit_targeting(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         enable_unit_targeting(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_technology_cost(	self,	source_player: int | None = None,	technology: int | None = None,	resource_1: int | None = None,	resource_1_quantity: int | None = None,	resource_2: int | None = None,	resource_2_quantity: int | None = None,	resource_3: int | None = None,	resource_3_quantity: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_technology_research_time(	self,	quantity: int | None = None,	source_player: int | None = None,	technology: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_technology_name(	self,	source_player: int | None = None,	technology: int | None = None,	string_id: int | None = None,	message: str | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_technology_description(	self,	source_player: int | None = None,	technology: int | None = None,	string_id: int | None = None,	message: str | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         enable_technology_stacking(	self,	source_player: int | None = None,	technology: int | None = None,	quantity: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         disable_technology_stacking(	self,	source_player: int | None = None,	technology: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         acknowledge_multiplayer_ai_signal(	self,	ai_signal_value: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         disable_object_selection(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         enable_object_selection(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_color_mood(self, quantity: int | None = None, color_mood: int | None = None):

### def         enable_object_deletion(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None):

### def         disable_object_deletion(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None):

### def         train_unit(	self,	quantity: int | None = None,	object_list_unit_id: int | None = None,	source_player: int | None = None,	location_x: int | None = None,	location_y: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None):

### def         initiate_research(	self,	source_player: int | None = None,	technology: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None):

### def         create_object_attack(	self,	armour_attack_quantity: int | None = None,	armour_attack_class: int | None = None,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	operation: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None):

### def         create_object_armor(	self,	armour_attack_quantity: int | None = None,	armour_attack_class: int | None = None,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	operation: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None):

### def         modify_attribute_by_variable(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	operation: int | None = None,	object_attributes: int | None = None,	variable: int | None = None,	message: str | None = None,	armour_attack_class: int | None = None):

### def         set_object_cost(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	quantity: int | None = None,	tribute_list: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         load_key_value(	self,	variable: int | None = None,	message: str | None = None,	quantity: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         store_key_value(	self,	variable: int | None = None,	message: str | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         delete_key(	self,	message: str | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_technology_icon(	self,	technology: int | None = None,	source_player: int | None = None,	quantity: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         change_technology_hotkey(	self,	technology: int | None = None,	source_player: int | None = None,	quantity: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         modify_variable_by_resource(	self,	tribute_list: int | None = None,	source_player: int | None = None,	operation: int | None = None,	variable: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         modify_variable_by_attribute(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	operation: int | None = None,	object_attributes: int | None = None,	variable: int | None = None,	message: str | None = None,	armour_attack_class: int | None = None):

### def         change_object_caption(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	string_id: int | None = None,	message: str | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None):

### def         change_player_color(	self,	source_player: int | None = None,	player_color: int | None = None):

### def         create_decision(	self,	decision_id: int | None = None,	string_id: int | None = None,	message: str | None = None,	string_id_option1: int | None = None,	message_option1: str | None = None,	string_id_option2: int | None = None,	message_option2: str | None = None):

### def         disable_unit_attackable(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         enable_unit_attackable(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	max_units_affected: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         modify_variable_by_variable(	self,	variable: int | None = None,	operation: int | None = None,	variable2: int | None = None):
How it works:

variable { operation }= variable2

Examples:

Operation.SET: variable = variable2
Operation.ADD: variable = variable + variable2
Operation.SUBTRACT: variable = variable - variable2
Operation.DIVIDE: variable = variable / variable2
Operation.MULTIPLY: variable = variable * variable2

### def         count_units_into_variable(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	variable2: int | None = None):

### def         add_train_location(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	object_list_unit_id_2: int | None = None,	button_location: int | None = None,	train_time: int | None = None,	hotkey: int | None = None):

### def         research_local_technology(	self,	local_technology: int | None = None,	source_player: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_list_unit_id_2: int | None = None):

### def         modify_attribute_for_class(	self,	object_group2: int | None = None,	object_type2: int | None = None,	source_player: int | None = None,	object_attributes: int | None = None,	message: int | None = None,	operation: int | None = None,	quantity: int | float | None = None,	armour_attack_quantity: int | None = None,	armour_attack_class: int | None = None):

### def         modify_object_attribute(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	object_attributes: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	operation: int | None = None,	message: str | None = None,	quantity: int | float | None = None,	armour_attack_quantity: int | None = None,	armour_attack_class: int | None = None,	object_filter: int | None = None):

### def         modify_object_attribute_by_variable(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	object_attributes: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	operation: int | None = None,	message: str | None = None,	variable: int | None = None,	armour_attack_class: int | None = None):

### def         change_object_visibility(	self,	source_player: int | None = None,	target_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	visibility_state: int | None = None,	max_units_affected: int | None = None,	selected_object_ids: int | None = None):

### def         build_object(	self,	object_list_unit_id: int | None = None,	source_player: int | None = None,	location_x: int | None = None,	location_y: int | None = None,	location_object_reference: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	wall_x1: int | None = None,	wall_y1: int | None = None,	wall_x2: int | None = None,	wall_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	building_list: int | None = None,	selected_object_ids: Union[int, List[int], NoneType] = None,	disable_garrison_unload_sound: int | None = None,	max_units_affected: int | None = None,	issue_group_command: int | None = None,	queue_action: int | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:

### def         mirror_diplomacy(	self,	source_player: int | None = None,	target_player: int | None = None,	enabled: bool | None = None) -> AoE2ScenarioParser.objects.data_objects.effect.Effect:


### class     NewConditionSupport:

### NewConditionSupport(trigger_ref)

### def         none(self) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         bring_object_to_area(	self,	unit_object: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         bring_object_to_object(	self,	unit_object: int | None = None,	next_object: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         own_objects(	self,	quantity: int | None = None,	object_list: int | None = None,	source_player: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	include_changeable_weapon_objects: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         own_fewer_objects(	self,	quantity: int | None = None,	object_list: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	include_changeable_weapon_objects: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         objects_in_area(	self,	quantity: int | None = None,	object_list: int | None = None,	source_player: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	inverted: int | None = None,	object_state: int | None = None,	include_changeable_weapon_objects: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         destroy_object(	self,	unit_object: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         capture_object(	self,	unit_object: int | None = None,	source_player: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         accumulate_attribute(	self,	quantity: int | None = None,	attribute: int | None = None,	source_player: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         research_technology(	self,	source_player: int | None = None,	technology: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         timer(	self,	timer: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         object_selected(	self,	unit_object: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         ai_signal(	self,	ai_signal: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         player_defeated(	self,	source_player: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         object_has_target(	self,	unit_object: int | None = None,	next_object: int | None = None,	object_list: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         object_visible(	self,	unit_object: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         object_not_visible(	self,	unit_object: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         researching_tech(	self,	source_player: int | None = None,	technology: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         units_garrisoned(	self,	quantity: int | None = None,	unit_object: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         difficulty_level(	self,	quantity: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         chance(	self,	quantity: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         technology_state(	self,	quantity: int | None = None,	source_player: int | None = None,	technology: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         variable_value(	self,	quantity: int | None = None,	inverted: int | None = None,	variable: int | None = None,	comparison: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         object_hp(	self,	quantity: int | None = None,	unit_object: int | None = None,	inverted: int | None = None,	comparison: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         diplomacy_state(	self,	quantity: int | None = None,	source_player: int | None = None,	inverted: int | None = None,	target_player: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         script_call(	self,	xs_function: str | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         object_visible_multiplayer(	self,	unit_object: int | None = None,	source_player: int | None = None,	allow_in_fog: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         object_selected_multiplayer(	self,	unit_object: int | None = None,	source_player: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         object_has_action(	self,	unit_object: int | None = None,	next_object: int | None = None,	object_list: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	inverted: int | None = None,	unit_ai_action: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         or_(self) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         ai_signal_multiplayer(	self,	ai_signal: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         and_(self) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         building_is_trading(	self,	unit_object: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         display_timer_triggered(	self,	timer_id: int | None = None,	inverted: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         victory_timer(	self,	quantity: int | None = None,	source_player: int | None = None,	inverted: int | None = None,	comparison: int | None = None,	victory_timer_type: int | None = None) -> AoE2ScenarioParser.objects.data_objects.condition.Condition:

### def         decision_triggered(	self,	inverted: int | None = None,	decision_id: int | None = None,	decision_option: int | None = None):

### def         object_attacked(	self,	object_list: int | None = None,	quantity: int | None = None,	source_player: int | None = None,	object_group: int | None = None,	object_type: int | None = None,	unit_object: int | None = None,	inverted: int | None = None):

### def         hero_power_cast(self, source_player: int | None = None):

### def         compare_variables(	self,	inverted: int | None = None,	variable: int | None = None,	comparison: int | None = None,	variable2: int | None = None):

### def         trigger_active(self, trigger_id: int | None = None, inverted: int | None = None):

### def         local_tech_researched(	self,	local_technology: int | None = None,	source_player: int | None = None,	unit_object: int | None = None,	area_x1: int | None = None,	area_y1: int | None = None,	area_x2: int | None = None,	area_y2: int | None = None,	inverted: int | None = None,	quantity: int | None = None):


### class     XsCheck:
If XS-Check is enabled or not

### XsCheck(uuid: uuid.UUID)

### version: Tuple[int, int, int]        = (0, 2, 32)

### enabled
If XS-Check is enabled or not

### xs_encoding
The encoding that should be used for reading and writing the file with the XS script

### allow_unsupported_versions: bool
If XS-Check should be checked for compatibility

### raise_on_error: bool
If a Python error should be raised if XS-Check encounters an error

### ignores: Set[str]
A set of warnings to ignore

### additional_args: List[str]
A list of additional arguments to append to the validation calls

### path: Optional[pathlib.Path]
The path for a custom XS check binary (One that is not shipped with AoE2ScenarioParser

### timeout_seconds
The timeout for the XS-Check call in seconds

### is_enabled

### is_disabled

### def         validate(	self,	xs_file: Union[pathlib.Path, str, NoneType],	show_tmpfile: bool = True) -> True:
Validates the XS file and throws an exception if xs-check finds an error

Args:
    xs_file: The XS file to validate
    show_tmpfile: If a reference to the tmp file should be displayed

Throws:
    XsCheckValidationError: When xs-check encounters an error

Returns:
    True if no errors are found or xs-check has been disabled, an XsCheckValidationError is thrown otherwise

### def         validate_safe(self, xs_file: Union[pathlib.Path, str, NoneType]) -> bool:
Validates the XS file and and returns a boolean based on if errors were found

Args:
    xs_file: The XS file to validate

Returns:
    True if no errors are found or xs-check has been disabled, False otherwise

### def         is_supported_xs_check_binary(self) -> bool:
Check if the xs-check binary is supported by this version of AoE2ScenarioParser.
Allows an override to easily allow users to use newer versions which might be supported too.

Returns:
    True if it is supported, False otherwise

### def         get_version(self) -> Tuple[int, ...]:
Get the version from the xs-check binary

Returns:
    A tuple containing the version xs-check number


---

## datasets（数据表与枚举）

这一组是本库最实用的部分：把 `UnitInfo` / `TechInfo` / `BuildingInfo` / `EffectId` / `ConditionId` 等全部枚举成员连同 `(ID, ICON_ID)` 元组一起导出，
等于拿到了"名字 → 游戏内 ID"的完整映射表，可以直接当查表用。


### datasets/


### class     BuildingInfo(AoE2ScenarioParser.datasets.support.info_dataset_base.InfoDatasetBase):
This is an enum class which provides information about most of the buildings in the game. Information about the
following properties of a building is found in this class:

- Unit ID

- Icon ID

- Dead Unit ID

- HotKey ID

- If the building is a gaia only unit (e.g. ruins)

Inherited Methods from class InfoDatasetBase

Examples

### RUINS        = <BuildingInfo.RUINS: (345, -1, -1, 16393, True)>

### AACHEN_CATHEDRAL        = <BuildingInfo.AACHEN_CATHEDRAL: (1622, 37, 1517, 16182, False)>

### AMPHITHEATRE        = <BuildingInfo.AMPHITHEATRE: (251, 58, 1514, 16572, False)>

### AQUEDUCT        = <BuildingInfo.AQUEDUCT: (231, 52, 1522, 16201, False)>

### ARCH_OF_CONSTANTINE        = <BuildingInfo.ARCH_OF_CONSTANTINE: (899, 37, 1485, 16572, False)>

### ARCHERY_RANGE        = <BuildingInfo.ARCHERY_RANGE: (87, 0, 1415, 16128, False)>

### ARMY_TENT_A        = <BuildingInfo.ARMY_TENT_A: (1196, 76, 1467, 16521, False)>

### ARMY_TENT_B        = <BuildingInfo.ARMY_TENT_B: (1197, 76, 1468, 16521, False)>

### ARMY_TENT_C        = <BuildingInfo.ARMY_TENT_C: (1198, 77, 1469, 16522, False)>

### ARMY_TENT_D        = <BuildingInfo.ARMY_TENT_D: (1199, 77, 1470, 16523, False)>

### ARMY_TENT_E        = <BuildingInfo.ARMY_TENT_E: (1200, 77, 1471, 16522, False)>

### BARRACKS        = <BuildingInfo.BARRACKS: (12, 2, 1402, 16135, False)>

### BLACKSMITH        = <BuildingInfo.BLACKSMITH: (103, 4, 1419, 16131, False)>

### BOMBARD_TOWER        = <BuildingInfo.BOMBARD_TOWER: (236, 42, 1439, 16156, False)>

### BRIDGE_A_BOTTOM        = <BuildingInfo.BRIDGE_A_BOTTOM: (607, -1, 144, 16513, False)>

### BRIDGE_A_BROKEN_BOTTOM        = <BuildingInfo.BRIDGE_A_BROKEN_BOTTOM: (740, -1, 144, 16643, False)>

### BRIDGE_A_BROKEN_TOP        = <BuildingInfo.BRIDGE_A_BROKEN_TOP: (739, -1, 144, 16642, False)>

### BRIDGE_A_CRACKED        = <BuildingInfo.BRIDGE_A_CRACKED: (738, -1, 144, 16641, False)>

### BRIDGE_A_MIDDLE        = <BuildingInfo.BRIDGE_A_MIDDLE: (606, -1, 144, 16512, False)>

### BRIDGE_A_TOP        = <BuildingInfo.BRIDGE_A_TOP: (605, -1, 144, 16511, False)>

### BRIDGE_B_BOTTOM        = <BuildingInfo.BRIDGE_B_BOTTOM: (610, -1, 144, 16516, False)>

### BRIDGE_B_BROKEN_BOTTOM        = <BuildingInfo.BRIDGE_B_BROKEN_BOTTOM: (743, -1, 144, 16646, False)>

### BRIDGE_B_BROKEN_TOP        = <BuildingInfo.BRIDGE_B_BROKEN_TOP: (742, -1, 144, 16645, False)>

### BRIDGE_B_CRACKED        = <BuildingInfo.BRIDGE_B_CRACKED: (741, -1, 144, 16644, False)>

### BRIDGE_B_MIDDLE        = <BuildingInfo.BRIDGE_B_MIDDLE: (609, -1, 144, 16515, False)>

### BRIDGE_B_TOP        = <BuildingInfo.BRIDGE_B_TOP: (608, -1, 144, 16514, False)>

### BRIDGE_C_BOTTOM        = <BuildingInfo.BRIDGE_C_BOTTOM: (1206, -1, 144, 16513, False)>

### BRIDGE_C_BROKEN_BOTTOM        = <BuildingInfo.BRIDGE_C_BROKEN_BOTTOM: (1212, -1, 144, 16643, False)>

### BRIDGE_C_BROKEN_TOP        = <BuildingInfo.BRIDGE_C_BROKEN_TOP: (1211, -1, 144, 16642, False)>

### BRIDGE_C_CRACKED        = <BuildingInfo.BRIDGE_C_CRACKED: (1210, -1, 144, 16641, False)>

### BRIDGE_C_MIDDLE        = <BuildingInfo.BRIDGE_C_MIDDLE: (1205, -1, 144, 16512, False)>

### BRIDGE_C_TOP        = <BuildingInfo.BRIDGE_C_TOP: (1204, -1, 144, 16511, False)>

### BRIDGE_D_BOTTOM        = <BuildingInfo.BRIDGE_D_BOTTOM: (1209, -1, 144, 16516, False)>

### BRIDGE_D_BROKEN_BOTTOM        = <BuildingInfo.BRIDGE_D_BROKEN_BOTTOM: (1215, -1, 144, 16646, False)>

### BRIDGE_D_BROKEN_TOP        = <BuildingInfo.BRIDGE_D_BROKEN_TOP: (1214, -1, 144, 16645, False)>

### BRIDGE_D_CRACKED        = <BuildingInfo.BRIDGE_D_CRACKED: (1213, -1, 144, 16644, False)>

### BRIDGE_D_MIDDLE        = <BuildingInfo.BRIDGE_D_MIDDLE: (1208, -1, 144, 16515, False)>

### BRIDGE_D_TOP        = <BuildingInfo.BRIDGE_D_TOP: (1207, -1, 144, 16514, False)>

### BRIDGE_E_BOTTOM        = <BuildingInfo.BRIDGE_E_BOTTOM: (1552, -1, 144, 16513, False)>

### BRIDGE_E_BROKEN_BOTTOM        = <BuildingInfo.BRIDGE_E_BROKEN_BOTTOM: (1558, -1, 144, 16643, False)>

### BRIDGE_E_BROKEN_TOP        = <BuildingInfo.BRIDGE_E_BROKEN_TOP: (1557, -1, 144, 16642, False)>

### BRIDGE_E_CRACKED        = <BuildingInfo.BRIDGE_E_CRACKED: (1556, -1, 144, 16641, False)>

### BRIDGE_E_MIDDLE        = <BuildingInfo.BRIDGE_E_MIDDLE: (1551, -1, 144, 16512, False)>

### BRIDGE_E_TOP        = <BuildingInfo.BRIDGE_E_TOP: (1550, -1, 144, 16511, False)>

### BRIDGE_F_BOTTOM        = <BuildingInfo.BRIDGE_F_BOTTOM: (1555, -1, 144, 16516, False)>

### BRIDGE_F_BROKEN_BOTTOM        = <BuildingInfo.BRIDGE_F_BROKEN_BOTTOM: (1561, -1, 144, 16646, False)>

### BRIDGE_F_BROKEN_TOP        = <BuildingInfo.BRIDGE_F_BROKEN_TOP: (1560, -1, 144, 16645, False)>

### BRIDGE_F_CRACKED        = <BuildingInfo.BRIDGE_F_CRACKED: (1559, -1, 144, 16644, False)>

### BRIDGE_F_MIDDLE        = <BuildingInfo.BRIDGE_F_MIDDLE: (1554, -1, 144, 16515, False)>

### BRIDGE_F_TOP        = <BuildingInfo.BRIDGE_F_TOP: (1553, -1, 144, 16514, False)>

### BRIDGE_PIECE_AB_END_A        = <BuildingInfo.BRIDGE_PIECE_AB_END_A: (1839, -1, 143, 16511, False)>

### BRIDGE_PIECE_AB_END_B        = <BuildingInfo.BRIDGE_PIECE_AB_END_B: (1840, -1, 143, 16513, False)>

### BRIDGE_PIECE_AB_END_C        = <BuildingInfo.BRIDGE_PIECE_AB_END_C: (1841, -1, 143, 16513, False)>

### BRIDGE_PIECE_AB_MIDDLE        = <BuildingInfo.BRIDGE_PIECE_AB_MIDDLE: (1842, -1, 143, 16512, False)>

### BRIDGE_PIECE_AB_BROKEN_A        = <BuildingInfo.BRIDGE_PIECE_AB_BROKEN_A: (1843, -1, 143, 16642, False)>

### BRIDGE_PIECE_AB_BROKEN_B        = <BuildingInfo.BRIDGE_PIECE_AB_BROKEN_B: (1844, -1, 143, 16642, False)>

### BRIDGE_PIECE_AB_BROKEN_C        = <BuildingInfo.BRIDGE_PIECE_AB_BROKEN_C: (1845, -1, 143, 16643, False)>

### BRIDGE_PIECE_AB_CRACKED        = <BuildingInfo.BRIDGE_PIECE_AB_CRACKED: (1846, -1, 144, 16641, False)>

### BRIDGE_PIECE_AB_RAILS        = <BuildingInfo.BRIDGE_PIECE_AB_RAILS: (1847, -1, -1, 16593, False)>

### CASTLE        = <BuildingInfo.CASTLE: (82, 7, 1430, 16142, False)>

### CATHEDRAL        = <BuildingInfo.CATHEDRAL: (599, 11, 1480, 16505, False)>

### CHAIN_WEST_TO_EAST        = <BuildingInfo.CHAIN_WEST_TO_EAST: (1398, 72, 144, 16186, False)>

### CHAIN_SOUTHWEST_TO_NORTHEAST        = <BuildingInfo.CHAIN_SOUTHWEST_TO_NORTHEAST: (1396, 72, 144, 16186, False)>

### CHAIN_NORTH_TO_SOUTH        = <BuildingInfo.CHAIN_NORTH_TO_SOUTH: (1399, 72, 144, 16186, False)>

### CHAIN_NORTHWEST_TO_SOUTHEAST        = <BuildingInfo.CHAIN_NORTHWEST_TO_SOUTHEAST: (1397, 72, 144, 16186, False)>

### CITY_GATE_WEST_TO_EAST        = <BuildingInfo.CITY_GATE_WEST_TO_EAST: (1587, 36, 1512, 16044, False)>

### CITY_GATE_SOUTHWEST_TO_NORTHEAST        = <BuildingInfo.CITY_GATE_SOUTHWEST_TO_NORTHEAST: (1579, 36, 1510, 16044, False)>

### CITY_GATE_NORTH_TO_SOUTH        = <BuildingInfo.CITY_GATE_NORTH_TO_SOUTH: (1591, 36, 1513, 16044, False)>

### CITY_GATE_NORTHWEST_TO_SOUTHEAST        = <BuildingInfo.CITY_GATE_NORTHWEST_TO_SOUTHEAST: (1583, 36, 1511, 16044, False)>

### CITY_WALL        = <BuildingInfo.CITY_WALL: (370, 32, 143, 16201, False)>

### COLOSSEUM        = <BuildingInfo.COLOSSEUM: (263, 58, 1520, 16505, False)>

### DOCK        = <BuildingInfo.DOCK: (45, 13, -1, 16144, False)>

### DORMITION_CATHEDRAL        = <BuildingInfo.DORMITION_CATHEDRAL: (1369, 37, 1493, 16182, False)>

### FARM        = <BuildingInfo.FARM: (50, 35, 357, 16149, False)>

### FEITORIA        = <BuildingInfo.FEITORIA: (1021, 53, 1446, 16159, False)>

### FENCE        = <BuildingInfo.FENCE: (1062, 73, 1065, 16797, False)>

### FIRE_TOWER        = <BuildingInfo.FIRE_TOWER: (190, 26, 1438, 16158, False)>

### FISH_TRAP        = <BuildingInfo.FISH_TRAP: (199, 41, 278, 16495, False)>

### FORTIFIED_PALISADE_WALL        = <BuildingInfo.FORTIFIED_PALISADE_WALL: (119, 30, 143, 16202, False)>

### FORTIFIED_TOWER        = <BuildingInfo.FORTIFIED_TOWER: (1102, 45, 1444, 16231, False)>

### FORTIFIED_WALL        = <BuildingInfo.FORTIFIED_WALL: (155, 32, 1509, 16204, False)>

### FORTRESS        = <BuildingInfo.FORTRESS: (33, 8, 1486, 16142, False)>

### GATE_NORTHWEST_TO_SOUTHEAST        = <BuildingInfo.GATE_NORTHWEST_TO_SOUTHEAST: (88, 36, 1501, 16185, False)>

### GATE_WEST_TO_EAST        = <BuildingInfo.GATE_WEST_TO_EAST: (659, 36, 1502, 16185, False)>

### GATE_SOUTHWEST_TO_NORTHEAST        = <BuildingInfo.GATE_SOUTHWEST_TO_NORTHEAST: (64, 36, 1500, 16185, False)>

### GATE_NORTH_TO_SOUTH        = <BuildingInfo.GATE_NORTH_TO_SOUTH: (667, 36, 1503, 16185, False)>

### GOL_GUMBAZ        = <BuildingInfo.GOL_GUMBAZ: (1217, 37, 1487, 16578, False)>

### GUARD_TOWER        = <BuildingInfo.GUARD_TOWER: (234, 27, 1437, 16154, False)>

### HARBOR        = <BuildingInfo.HARBOR: (1189, 56, -1, 16144, False)>

### HOUSE        = <BuildingInfo.HOUSE: (70, 34, 1403, 16344, False)>

### HUT_A        = <BuildingInfo.HUT_A: (1082, 75, 1455, 16221, False)>

### HUT_B        = <BuildingInfo.HUT_B: (1083, 75, 1456, 16221, False)>

### HUT_C        = <BuildingInfo.HUT_C: (1084, 74, 1457, 16221, False)>

### HUT_D        = <BuildingInfo.HUT_D: (1085, 75, 1458, 16221, False)>

### HUT_E        = <BuildingInfo.HUT_E: (1086, 75, 1459, 16221, False)>

### HUT_F        = <BuildingInfo.HUT_F: (1087, 75, 1460, 16221, False)>

### HUT_G        = <BuildingInfo.HUT_G: (1088, 75, 1461, 16221, False)>

### KEEP        = <BuildingInfo.KEEP: (235, 26, 1438, 16155, False)>

### KREPOST        = <BuildingInfo.KREPOST: (1251, 55, 1479, 16349, False)>

### LUMBER_CAMP        = <BuildingInfo.LUMBER_CAMP: (562, 40, 1409, 16464, False)>

### MARKET        = <BuildingInfo.MARKET: (84, 16, 1422, 16161, False)>

### MILL        = <BuildingInfo.MILL: (68, 19, 1404, 16157, False)>

### MINING_CAMP        = <BuildingInfo.MINING_CAMP: (584, 39, 1410, 16487, False)>

### MONASTERY        = <BuildingInfo.MONASTERY: (104, 10, 1421, 16138, False)>

### MONUMENT        = <BuildingInfo.MONUMENT: (826, 37, -1, 16726, False)>

### OUTPOST        = <BuildingInfo.OUTPOST: (598, 38, 1405, 16504, False)>

### PALISADE_GATE_SOUTHWEST_TO_NORTHEAST        = <BuildingInfo.PALISADE_GATE_SOUTHWEST_TO_NORTHEAST: (789, 44, 1440, 16186, False)>

### PALISADE_GATE_WEST_TO_EAST        = <BuildingInfo.PALISADE_GATE_WEST_TO_EAST: (797, 44, 1442, 16186, False)>

### PALISADE_GATE_NORTHWEST_TO_SOUTHEAST        = <BuildingInfo.PALISADE_GATE_NORTHWEST_TO_SOUTHEAST: (793, 44, 1441, 16186, False)>

### PALISADE_GATE_NORTH_TO_SOUTH        = <BuildingInfo.PALISADE_GATE_NORTH_TO_SOUTH: (801, 44, 1443, 16186, False)>

### PALISADE_WALL        = <BuildingInfo.PALISADE_WALL: (72, 30, 1407, 16202, False)>

### PYRAMID        = <BuildingInfo.PYRAMID: (689, 57, 1515, 16571, False)>

### QUIMPER_CATHEDRAL        = <BuildingInfo.QUIMPER_CATHEDRAL: (872, 37, 1489, 16572, False)>

### RICE_FARM        = <BuildingInfo.RICE_FARM: (1187, 35, 1188, -1, False)>

### ROCK_CHURCH        = <BuildingInfo.ROCK_CHURCH: (1378, 37, -1, 16182, False)>

### SANCHI_STUPA        = <BuildingInfo.SANCHI_STUPA: (1216, 37, 1490, 16578, False)>

### SANKORE_MADRASAH        = <BuildingInfo.SANKORE_MADRASAH: (1367, 37, 1491, 16182, False)>

### SEA_GATE_SOUTHWEST_TO_NORTHEAST        = <BuildingInfo.SEA_GATE_SOUTHWEST_TO_NORTHEAST: (1379, 71, -1, 16186, False)>

### SEA_GATE_NORTH_TO_SOUTH        = <BuildingInfo.SEA_GATE_NORTH_TO_SOUTH: (1391, 71, -1, 16186, False)>

### SEA_GATE_WEST_TO_EAST        = <BuildingInfo.SEA_GATE_WEST_TO_EAST: (1387, 71, -1, 16186, False)>

### SEA_GATE_NORTHWEST_TO_SOUTHEAST        = <BuildingInfo.SEA_GATE_NORTHWEST_TO_SOUTHEAST: (1383, 71, -1, 16186, False)>

### SEA_TOWER        = <BuildingInfo.SEA_TOWER: (785, 25, -1, 16704, False)>

### SEA_WALL        = <BuildingInfo.SEA_WALL: (788, 92, -1, 16707, False)>

### SHRINE        = <BuildingInfo.SHRINE: (1264, 12, 1483, 16138, False)>

### SIEGE_WORKSHOP        = <BuildingInfo.SIEGE_WORKSHOP: (49, 22, 1425, 16169, False)>

### STABLE        = <BuildingInfo.STABLE: (101, 23, 1417, 16171, False)>

### STONE_WALL        = <BuildingInfo.STONE_WALL: (117, 31, 1508, 16203, False)>

### STORAGE        = <BuildingInfo.STORAGE: (1081, 59, 1484, 16219, False)>

### TEMPLE_OF_HEAVEN        = <BuildingInfo.TEMPLE_OF_HEAVEN: (637, 11, 1481, 16505, False)>

### TENT_A        = <BuildingInfo.TENT_A: (1097, 78, 1462, 16230, False)>

### TENT_B        = <BuildingInfo.TENT_B: (1098, 83, 1463, 16230, False)>

### TENT_C        = <BuildingInfo.TENT_C: (1099, 83, 1464, 16230, False)>

### TENT_D        = <BuildingInfo.TENT_D: (1100, 83, 1465, 16230, False)>

### TENT_E        = <BuildingInfo.TENT_E: (1101, 83, 1466, 16230, False)>

### TOWER_OF_LONDON        = <BuildingInfo.TOWER_OF_LONDON: (1368, 37, 1492, 16182, False)>

### TOWN_CENTER        = <BuildingInfo.TOWN_CENTER: (109, 28, 1408, 16164, False)>

### TRADE_WORKSHOP        = <BuildingInfo.TRADE_WORKSHOP: (110, 17, 1429, 16174, False)>

### UNIVERSITY        = <BuildingInfo.UNIVERSITY: (209, 33, 1427, 16176, False)>

### WATCH_TOWER        = <BuildingInfo.WATCH_TOWER: (79, 25, 1436, 16178, False)>

### WONDER        = <BuildingInfo.WONDER: (276, 37, 1445, 16182, False)>

### WOODEN_BRIDGE_A_BOTTOM        = <BuildingInfo.WOODEN_BRIDGE_A_BOTTOM: (1311, -1, 144, 16513, False)>

### WOODEN_BRIDGE_A_MIDDLE        = <BuildingInfo.WOODEN_BRIDGE_A_MIDDLE: (1310, -1, 144, 16512, False)>

### WOODEN_BRIDGE_A_TOP        = <BuildingInfo.WOODEN_BRIDGE_A_TOP: (1309, -1, 144, 16511, False)>

### WOODEN_BRIDGE_B_BOTTOM        = <BuildingInfo.WOODEN_BRIDGE_B_BOTTOM: (1314, -1, 144, 16516, False)>

### WOODEN_BRIDGE_B_MIDDLE        = <BuildingInfo.WOODEN_BRIDGE_B_MIDDLE: (1313, -1, 144, 16515, False)>

### WOODEN_BRIDGE_B_TOP        = <BuildingInfo.WOODEN_BRIDGE_B_TOP: (1312, -1, 144, 16514, False)>

### YURT_A        = <BuildingInfo.YURT_A: (712, 81, 1447, 16594, False)>

### YURT_B        = <BuildingInfo.YURT_B: (713, 82, 1448, 16595, False)>

### YURT_C        = <BuildingInfo.YURT_C: (714, 82, 1449, 16596, False)>

### YURT_D        = <BuildingInfo.YURT_D: (715, 82, 1450, 16597, False)>

### YURT_E        = <BuildingInfo.YURT_E: (716, 80, 1451, 16598, False)>

### YURT_F        = <BuildingInfo.YURT_F: (717, 80, 1452, 16599, False)>

### YURT_G        = <BuildingInfo.YURT_G: (718, 80, 1453, 16600, False)>

### YURT_H        = <BuildingInfo.YURT_H: (719, 79, 1454, 16601, False)>

### YURT_I        = <BuildingInfo.YURT_I: (1832, 90, 1532, 16598, False)>

### YURT_J        = <BuildingInfo.YURT_J: (1833, 90, 1533, 16599, False)>

### YURT_K        = <BuildingInfo.YURT_K: (1834, 90, 1534, 16600, False)>

### YURT_L        = <BuildingInfo.YURT_L: (1835, 91, 1535, 16601, False)>

### DONJON        = <BuildingInfo.DONJON: (1665, 84, 1524, 16350, False)>

### TRADE_WORKSHOP_BR        = <BuildingInfo.TRADE_WORKSHOP_BR: (1647, 17, 1429, 16174, False)>

### TRADE_WORKSHOP_TG        = <BuildingInfo.TRADE_WORKSHOP_TG: (179, 17, 1429, 16174, False)>

### TOWN_CENTER_PACKED        = <BuildingInfo.TOWN_CENTER_PACKED: (444, 264, 1274, 16311, False)>

### FOLWARK        = <BuildingInfo.FOLWARK: (1734, 86, 1528, 16157, False)>

### FORTIFIED_GATE_SOUTHWEST_TO_NORTHEAST        = <BuildingInfo.FORTIFIED_GATE_SOUTHWEST_TO_NORTHEAST: (63, 36, 1504, 16185, False)>

### FORTIFIED_GATE_NORTHWEST_TO_SOUTHEAST        = <BuildingInfo.FORTIFIED_GATE_NORTHWEST_TO_SOUTHEAST: (85, 36, 1505, 16185, False)>

### FORTIFIED_GATE_WEST_TO_EAST        = <BuildingInfo.FORTIFIED_GATE_WEST_TO_EAST: (660, 36, 1506, 16185, False)>

### FORTIFIED_GATE_NORTH_TO_SOUTH        = <BuildingInfo.FORTIFIED_GATE_NORTH_TO_SOUTH: (668, 36, 1507, 16185, False)>

### PAGAN_SHRINE        = <BuildingInfo.PAGAN_SHRINE: (1712, 85, 1526, 16159, False)>

### GATE        = <BuildingInfo.GATE: (487, 36, 1406, 16185, False)>

### PALISADE_GATE        = <BuildingInfo.PALISADE_GATE: (792, 44, 1406, 16186, False)>

### FORTIFIED_GATE        = <BuildingInfo.FORTIFIED_GATE: (488, 36, 1406, 16185, False)>

### CARAVANSERAI        = <BuildingInfo.CARAVANSERAI: (1754, 87, 1529, 16351, False)>

### MINARET_OF_JAM        = <BuildingInfo.MINARET_OF_JAM: (1773, 37, 1530, 16182, False)>

### FORTIFIED_CHURCH        = <BuildingInfo.FORTIFIED_CHURCH: (1806, 88, 1531, 16138, False)>

### MULE_CART        = <BuildingInfo.MULE_CART: (1808, 89, 1809, 16352, False)>

### SHIPYARD        = <BuildingInfo.SHIPYARD: (2119, 111, -1, 416002, False)>

### PORT        = <BuildingInfo.PORT: (2172, 110, -1, 416001, False)>

### GREEK_ARMY_TENT        = <BuildingInfo.GREEK_ARMY_TENT: (2176, 77, 2177, 16522, False)>

### GREEK_COMMANDER_TENT        = <BuildingInfo.GREEK_COMMANDER_TENT: (2262, 77, 2263, 16522, False)>

### SAPPER_TUNNEL        = <BuildingInfo.SAPPER_TUNNEL: (2281, 112, 144, 16717, False)>

### ORACLES_TEMPLE        = <BuildingInfo.ORACLES_TEMPLE: (2348, 10, 1421, -1, False)>

### POENARI_CASTLE        = <BuildingInfo.POENARI_CASTLE: (445, 7, 1488, 16318, False)>

### PAVILION_A        = <BuildingInfo.PAVILION_A: (624, 93, 1476, 16521, False)>

### PAVILION_C        = <BuildingInfo.PAVILION_C: (625, 43, 1478, 16523, False)>

### PAVILION_B        = <BuildingInfo.PAVILION_B: (626, 43, 1477, 16522, False)>

### MOSQUE        = <BuildingInfo.MOSQUE: (655, 12, 1496, 16552, False)>

### THE_ACCURSED_TOWER        = <BuildingInfo.THE_ACCURSED_TOWER: (684, 45, 1494, 16566, False)>

### THE_TOWER_OF_FLIES        = <BuildingInfo.THE_TOWER_OF_FLIES: (685, 45, 1495, 16567, False)>

### DOME_OF_THE_ROCK        = <BuildingInfo.DOME_OF_THE_ROCK: (690, 37, 1482, 16572, False)>

### GREAT_PYRAMID        = <BuildingInfo.GREAT_PYRAMID: (696, 57, 1516, 16578, False)>

### BARRICADE_A        = <BuildingInfo.BARRICADE_A: (1090, 54, 1472, 16223, False)>

### BARRICADE_B        = <BuildingInfo.BARRICADE_B: (1218, 54, 1473, 16223, False)>

### BARRICADE_C        = <BuildingInfo.BARRICADE_C: (1219, 54, 1474, 16223, False)>

### BARRICADE_D        = <BuildingInfo.BARRICADE_D: (1220, 54, 1475, 16223, False)>

### CHIEFS_YURT        = <BuildingInfo.CHIEFS_YURT: (1870, 91, 1871, 16159, False)>

### BROKEN_FENCE_A        = <BuildingInfo.BROKEN_FENCE_A: (1885, -1, -1, 16464, False)>

### BROKEN_FENCE_B        = <BuildingInfo.BROKEN_FENCE_B: (1886, -1, -1, 16464, False)>

### PASTURE        = <BuildingInfo.PASTURE: (1897, 96, 1898, 16164, False)>

### BRIDGE_PIECE_CD_END_A        = <BuildingInfo.BRIDGE_PIECE_CD_END_A: (1992, -1, 143, 16513, False)>

### BRIDGE_PIECE_CD_END_B        = <BuildingInfo.BRIDGE_PIECE_CD_END_B: (1993, -1, 143, 16513, False)>

### BRIDGE_PIECE_CD_END_C        = <BuildingInfo.BRIDGE_PIECE_CD_END_C: (1994, -1, 143, 16513, False)>

### BRIDGE_PIECE_CD_MIDDLE_A        = <BuildingInfo.BRIDGE_PIECE_CD_MIDDLE_A: (1995, -1, 143, 16512, False)>

### BRIDGE_PIECE_CD_MIDDLE_B        = <BuildingInfo.BRIDGE_PIECE_CD_MIDDLE_B: (1996, -1, 143, 16512, False)>

### BRIDGE_PIECE_CD_MIDDLE_C        = <BuildingInfo.BRIDGE_PIECE_CD_MIDDLE_C: (1997, -1, 143, 16512, False)>

### BRIDGE_PIECE_CD_BROKEN_A        = <BuildingInfo.BRIDGE_PIECE_CD_BROKEN_A: (1998, -1, 143, 16642, False)>

### BRIDGE_PIECE_CD_BROKEN_B        = <BuildingInfo.BRIDGE_PIECE_CD_BROKEN_B: (1999, -1, 143, 16642, False)>

### BRIDGE_PIECE_CD_BROKEN_C        = <BuildingInfo.BRIDGE_PIECE_CD_BROKEN_C: (2000, -1, 143, 16643, False)>

### BRIDGE_PIECE_CD_CRACKED        = <BuildingInfo.BRIDGE_PIECE_CD_CRACKED: (2001, -1, 144, 16641, False)>

### BRIDGE_PIECE_CD_RAILS_A        = <BuildingInfo.BRIDGE_PIECE_CD_RAILS_A: (2002, -1, -1, 16593, False)>

### BRIDGE_PIECE_CD_RAILS_B        = <BuildingInfo.BRIDGE_PIECE_CD_RAILS_B: (2003, -1, -1, 16593, False)>

### BRIDGE_PIECE_CD_RAILS_C        = <BuildingInfo.BRIDGE_PIECE_CD_RAILS_C: (2004, -1, -1, 16593, False)>

### YURT_M        = <BuildingInfo.YURT_M: (2033, 97, 1534, 16600, False)>

### HALL_OF_HEROES        = <BuildingInfo.HALL_OF_HEROES: (2060, 95, 145, 16349, False)>

### GREEK_COMMANDER_TENT_DROPSITE        = <BuildingInfo.GREEK_COMMANDER_TENT_DROPSITE: (2405, 77, 2263, 16522, False)>

### SUPPLY_CART_A        = <BuildingInfo.SUPPLY_CART_A: (2412, 34, 205, 16100, False)>

### SUPPLY_CART_B        = <BuildingInfo.SUPPLY_CART_B: (2413, 34, 178, 16100, False)>

### MACEDONIAN_COMMAND_POST        = <BuildingInfo.MACEDONIAN_COMMAND_POST: (2414, 115, 2476, 416032, False)>

### FORTIFIED_OUTPOST        = <BuildingInfo.FORTIFIED_OUTPOST: (2415, 116, 2489, 16504, False)>

### MOLE        = <BuildingInfo.MOLE: (2421, -1, 144, 16515, False)>

### MOLE_CONSTRUCTED        = <BuildingInfo.MOLE_CONSTRUCTED: (2422, -1, 144, 16515, False)>

### CAMP_BARRACKS        = <BuildingInfo.CAMP_BARRACKS: (2437, 2, 2496, 16135, False)>

### CAMP_ARCHERY_RANGE        = <BuildingInfo.CAMP_ARCHERY_RANGE: (2438, 0, 2492, 16128, False)>

### CAMP_STABLE        = <BuildingInfo.CAMP_STABLE: (2439, 23, 2406, 16171, False)>

### FLAGSHIP_OF_NEARCHOS_MOVEABLE        = <BuildingInfo.FLAGSHIP_OF_NEARCHOS_MOVEABLE: (2442, 749, -1, 416012, False)>

### HELEPOLIS        = <BuildingInfo.HELEPOLIS: (2443, 113, 2484, 416033, False)>

### FLAGSHIP_OF_NEARCHOS_DOCKED_MOVEABLE        = <BuildingInfo.FLAGSHIP_OF_NEARCHOS_DOCKED_MOVEABLE: (2448, 114, -1, 416012, False)>

### MOLE_TOP        = <BuildingInfo.MOLE_TOP: (2521, -1, 144, 16514, False)>

### MOLE_BOTTOM        = <BuildingInfo.MOLE_BOTTOM: (2522, -1, 144, 16516, False)>

### SETTLEMENT        = <BuildingInfo.SETTLEMENT: (2556, 98, 145, 16353, False)>

### WOODEN_FORT        = <BuildingInfo.WOODEN_FORT: (2600, 9, 146, 16142, False)>

### FORT_WALL        = <BuildingInfo.FORT_WALL: (2678, 30, 143, 16202, False)>

### FORT_GATE_SOUTHWEST_TO_NORTHEAST        = <BuildingInfo.FORT_GATE_SOUTHWEST_TO_NORTHEAST: (2679, 36, 1510, 16044, False)>

### FORT_GATE_NORTHWEST_TO_SOUTHEAST        = <BuildingInfo.FORT_GATE_NORTHWEST_TO_SOUTHEAST: (2683, 36, 1511, 16044, False)>

### FORT_GATE_WEST_TO_EAST        = <BuildingInfo.FORT_GATE_WEST_TO_EAST: (2687, 36, 1512, 16044, False)>

### FORT_GATE_NORTH_TO_SOUTH        = <BuildingInfo.FORT_GATE_NORTH_TO_SOUTH: (2691, 36, 1513, 16044, False)>

### WOODEN_BRIDGE_PIECE_END_A        = <BuildingInfo.WOODEN_BRIDGE_PIECE_END_A: (2037, -1, 143, 16511, False)>

### WOODEN_BRIDGE_PIECE_END_B        = <BuildingInfo.WOODEN_BRIDGE_PIECE_END_B: (2039, -1, 143, 16513, False)>

### WOODEN_BRIDGE_PIECE_END_C        = <BuildingInfo.WOODEN_BRIDGE_PIECE_END_C: (2041, -1, 143, 16513, False)>

### WOODEN_BRIDGE_PIECE_MIDDLE        = <BuildingInfo.WOODEN_BRIDGE_PIECE_MIDDLE: (2043, -1, 143, 16512, False)>

### WOODEN_BRIDGE_PIECE_RAILS        = <BuildingInfo.WOODEN_BRIDGE_PIECE_RAILS: (2081, -1, -1, 16593, False)>

### LONGHOUSE_A        = <BuildingInfo.LONGHOUSE_A: (2559, 34, 144, 16521, False)>

### LONGHOUSE_B        = <BuildingInfo.LONGHOUSE_B: (2561, 34, 144, 16521, False)>

### ARMY_TENT_F        = <BuildingInfo.ARMY_TENT_F: (2745, 76, 143, 16521, False)>


### class     ConditionId(enum.IntEnum):
This enum class provides the integer values used to reference the conditions in the game. Used in every condition
to indicate which type of condition it is

Examples

### empty_attributes        =              {'condition_type': -1, 'quantity': -1, 'attribute': -1, 'unit_object': -1, 'next_object': -1, 'object_list': -1, 'source_player': -1, 'technology': -1, 'timer': -1, 'trigger_id': -1, 'area_x1': -1, 'area_y1': -1, 'area_x2': -1, 'area_y2': -1, 'object_group': -1, 'object_type': -1, 'ai_signal': -1, 'inverted': -1, 'variable': -1, 'comparison': -1, 'target_player': -1, 'unit_ai_action': -1, 'object_state': -1, 'timer_id': -1, 'victory_timer_type': -1, 'include_changeable_weapon_objects': -1, 'decision_id': -1, 'decision_option': -1, 'variable2': '', 'local_technology': -1, 'allow_in_fog': -1, 'xs_function': ''}

### condition_names        = {}

### default_attributes        = {}

### attributes        = {}

### attribute_presentation        = {}
This dict maps the condition attributes by their name to the dataset used to represent them

### NONE        = <ConditionId.NONE: 0>
Attributes for the none  condition are:

... It's called none... What parameters do you think it has?! ❤

### BRING_OBJECT_TO_AREA        = <ConditionId.BRING_OBJECT_TO_AREA: 1>
Attributes for the bring_object_to_area condition are:

- unit_object

- area_x1

- area_y1

- area_x2

- area_y2

- inverted

### BRING_OBJECT_TO_OBJECT        = <ConditionId.BRING_OBJECT_TO_OBJECT: 2>
Attributes for the bring_object_to_object condition are:

- unit_object

- next_object

- inverted

### OWN_OBJECTS        = <ConditionId.OWN_OBJECTS: 3>
Attributes for the own_objects condition are:

- quantity

- object_list

- source_player

- object_group

- object_type

- include_changeable_weapon_objects

### OWN_FEWER_OBJECTS        = <ConditionId.OWN_FEWER_OBJECTS: 4>
Attributes for the own_fewer_objects condition are:

- quantity

- object_list

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- include_changeable_weapon_objects

### OBJECTS_IN_AREA        = <ConditionId.OBJECTS_IN_AREA: 5>
Attributes for the object_in_area condition are:

- quantity

- object_list

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- object_state

- inverted

- include_changeable_weapon_objects

### DESTROY_OBJECT        = <ConditionId.DESTROY_OBJECT: 6>
Attributes for the destroy_object condition are:

- unit_object

- inverted

### CAPTURE_OBJECT        = <ConditionId.CAPTURE_OBJECT: 7>
Attributes for the capture_object condition are:

- unit_object

- source_player

- inverted

### ACCUMULATE_ATTRIBUTE        = <ConditionId.ACCUMULATE_ATTRIBUTE: 8>
Attributes for the accumulate_attribute condition are:

- quantity

- attribute

- source_player

- inverted

### RESEARCH_TECHNOLOGY        = <ConditionId.RESEARCH_TECHNOLOGY: 9>
Attributes for the research_technology condition are:

- source_player

- technology

- inverted

### TIMER        = <ConditionId.TIMER: 10>
Attributes for the timer condition are:

- timer

- inverted

### OBJECT_SELECTED        = <ConditionId.OBJECT_SELECTED: 11>
Attributes for the object_selected condition are:

- unit_object

- inverted

### AI_SIGNAL        = <ConditionId.AI_SIGNAL: 12>
Attributes for the ai_signal condition are:

- ai_signal

- inverted

### PLAYER_DEFEATED        = <ConditionId.PLAYER_DEFEATED: 13>
Attributes for the player_defeated condition are:

- source_player

- inverted

### OBJECT_HAS_TARGET        = <ConditionId.OBJECT_HAS_TARGET: 14>
Attributes for the object_has_target condition are:

- unit_object

- next_object

- object_list

- object_group

- object_type

- inverted

### OBJECT_VISIBLE        = <ConditionId.OBJECT_VISIBLE: 15>
Attributes for the object_visible condition are:

- unit_object

### OBJECT_NOT_VISIBLE        = <ConditionId.OBJECT_NOT_VISIBLE: 16>
Attributes for the object_not_visible condition are:

- unit_object

### RESEARCHING_TECH        = <ConditionId.RESEARCHING_TECH: 17>
Attributes for the researching_tech condition are:

- source_player

- technology

- inverted

### UNITS_GARRISONED        = <ConditionId.UNITS_GARRISONED: 18>
Attributes for the units_garrisoned condition are:

- quantity

- unit_object

- inverted

### DIFFICULTY_LEVEL        = <ConditionId.DIFFICULTY_LEVEL: 19>
Attributes for the difficulty_level condition are:

- condition_type

- quantity

- inverted

### CHANCE        = <ConditionId.CHANCE: 20>
Attributes for the chance condition are:

- quantity

### TECHNOLOGY_STATE        = <ConditionId.TECHNOLOGY_STATE: 21>
Attributes for the technology_state condition are:

- quantity

- source_player

- technology

- inverted

### VARIABLE_VALUE        = <ConditionId.VARIABLE_VALUE: 22>
Attributes for the variable_value condition are:

- quantity

- inverted

- variable

- comparison

### OBJECT_HP        = <ConditionId.OBJECT_HP: 23>
Attributes for the object_hp condition are:

- quantity

- unit_object

- inverted

- comparison

### DIPLOMACY_STATE        = <ConditionId.DIPLOMACY_STATE: 24>
Attributes for the diplomacy_state condition are:

- quantity

- source_player

- inverted

- target_player

### SCRIPT_CALL        = <ConditionId.SCRIPT_CALL: 25>
Attributes for the script_call condition are:

- xs_function

This condition was added in: 1.40

### OBJECT_SELECTED_MULTIPLAYER        = <ConditionId.OBJECT_SELECTED_MULTIPLAYER: 26>
Attributes for the object_selected_multiplayer condition are:

- unit_object

- source_player

- inverted

This condition was added in: 1.40

### OBJECT_VISIBLE_MULTIPLAYER        = <ConditionId.OBJECT_VISIBLE_MULTIPLAYER: 27>
Attributes for the object_visible_multiplayer condition are:

- unit_object

- source_player

- inverted

- allow_in_fog

This condition was added in: 1.40

### OBJECT_HAS_ACTION        = <ConditionId.OBJECT_HAS_ACTION: 28>
Attributes for the object_has_action condition are:

- unit_object

- next_object

- inverted

- unit_ai_action

This condition was added in: 1.40

### OR        = <ConditionId.OR: 29>
The OR condition does not have any attributes

This condition was added in: 1.40

### AI_SIGNAL_MULTIPLAYER        = <ConditionId.AI_SIGNAL_MULTIPLAYER: 30>
Attributes for the ai_signal_multiplayer condition are:

- ai_signal

- inverted

This condition was added in: 1.40

### BUILDING_IS_TRADING        = <ConditionId.BUILDING_IS_TRADING: 54>
Attributes for the building_is_trading condition are:

- unit_object

- inverted

This condition was added in: 1.46

### DISPLAY_TIMER_TRIGGERED        = <ConditionId.DISPLAY_TIMER_TRIGGERED: 55>
Attributes for the display_timer_triggered condition are:

- timer_id

- inverted

This condition was added in: 1.46

### VICTORY_TIMER        = <ConditionId.VICTORY_TIMER: 56>
Attributes for the victory_timer condition are:

- quantity

- source_player

- inverted

- comparison

- victory_timer_type

This condition was added in: 1.46

### AND        = <ConditionId.AND: 57>
The AND condition does not have any attributes

This condition was added in: 1.46

### DECISION_TRIGGERED        = <ConditionId.DECISION_TRIGGERED: 75>
Attributes for the decision_triggered condition are:

- inverted

- decision_id

- decision_option

This condition was added in: 1.54 (Trigger version 4.1)

### OBJECT_ATTACKED        = <ConditionId.OBJECT_ATTACKED: 76>
Attributes for the object_attacked condition are:

- object_list

- quantity

- source_player

- object_group

- object_type

- unit_object

- inverted

This condition was added in: 1.54 (Trigger version 4.1)

### HERO_POWER_CAST        = <ConditionId.HERO_POWER_CAST: 77>
Attributes for the hero_power_cast condition are:

- source_player

This condition was added in: 1.54 (Trigger version 4.1)

### COMPARE_VARIABLES        = <ConditionId.COMPARE_VARIABLES: 78>
Attributes for the compare_variables condition are:

- inverted

- variable

- comparison

- variable2

This condition was added in: 1.54 (Trigger version 4.1)

### TRIGGER_ACTIVE        = <ConditionId.TRIGGER_ACTIVE: 79>
Attributes for the trigger_active condition are:

- trigger_id

- inverted

This condition was added in: 1.54 (Trigger version 4.1)

### LOCAL_TECH_RESEARCHED        = <ConditionId.LOCAL_TECH_RESEARCHED: 80>
Attributes for the local_tech_researched condition are:

- local_technology

- source_player

- unit_object

- area_x1

- area_y1

- area_x2

- area_y2

- inverted

- quantity
This condition was added in: 1.55 (Trigger version 4.5)


### class     EffectId(enum.IntEnum):
This enum class provides the integer values used to reference the effects in the game. Used in every effect to
indicate which type of effect it is

Examples

### empty_attributes        =              {'effect_type': -1, 'ai_script_goal': -1, 'armour_attack_quantity': -1, 'armour_attack_class': -1, 'quantity': -1, 'tribute_list': -1, 'diplomacy': -1, 'object_list_unit_id': -1, 'source_player': -1, 'target_player': -1, 'technology': -1, 'string_id': -1, 'display_time': -1, 'trigger_id': -1, 'location_x': -1, 'location_y': -1, 'location_object_reference': -1, 'area_x1': -1, 'area_y1': -1, 'area_x2': -1, 'area_y2': -1, 'object_group': -1, 'object_type': -1, 'instruction_panel_position': -1, 'attack_stance': -1, 'time_unit': -1, 'enabled': -1, 'food': -1, 'wood': -1, 'stone': -1, 'gold': -1, 'item_id': -1, 'flash_object': -1, 'force_research_technology': -1, 'visibility_state': -1, 'scroll': -1, 'operation': -1, 'object_list_unit_id_2': -1, 'button_location': -1, 'ai_signal_value': -1, 'object_attributes': -1, 'variable': -1, 'timer': -1, 'facet': -1, 'play_sound': -1, 'player_color': -1, 'color_mood': -1, 'reset_timer': -1, 'object_state': -1, 'action_type': -1, 'resource_1': -1, 'resource_1_quantity': -1, 'resource_2': -1, 'resource_2_quantity': -1, 'resource_3': -1, 'resource_3_quantity': -1, 'decision_id': -1, 'string_id_option1': -1, 'string_id_option2': -1, 'variable2': -1, 'max_units_affected': -1, 'disable_garrison_unload_sound': -1, 'hotkey': -1, 'train_time': -1, 'local_technology': -1, 'disable_sound': -1, 'object_group2': -1, 'quantity_float': -1, 'facet2': -1, 'global_sound': -1, 'issue_group_command': -1, 'queue_action': -1, 'mutual_diplomacy': -1, 'wall_x1': -1, 'wall_y1': -1, 'wall_x2': -1, 'wall_y2': -1, 'object_filter': -1, 'use_tag_color_for_icon': -1, 'message': '', 'sound_name': '', 'selected_object_ids': -1, 'message_option1': '', 'message_option2': ''}

### effect_names        = {}

### default_attributes        = {}

### attributes        = {}

### attribute_presentation        = {}
This dict maps the effect attributes by their name to the dataset used to represent them

### NONE        = <EffectId.NONE: 0>
Attributes for the none effect are:

... none... Just like Conditions... People these days...

### CHANGE_DIPLOMACY        = <EffectId.CHANGE_DIPLOMACY: 1>
Attributes for the change_diplomacy effect are:

- diplomacy

- source_player

- target_player

### RESEARCH_TECHNOLOGY        = <EffectId.RESEARCH_TECHNOLOGY: 2>
Attributes for the research_technology effect are:

- source_player

- technology

- force_research_technology

### SEND_CHAT        = <EffectId.SEND_CHAT: 3>
Attributes for the send_chat effect are:

- source_player

- string_id

- message

- sound_name

### PLAY_SOUND        = <EffectId.PLAY_SOUND: 4>
Attributes for the play_sound effect are:

- source_player

- location_x

- location_y

- location_object_reference

- global_sound

- sound_name

### TRIBUTE        = <EffectId.TRIBUTE: 5>
Attributes for the tribute effect are:

- quantity

- tribute_list

- source_player

- target_player

### UNLOCK_GATE        = <EffectId.UNLOCK_GATE: 6>
Attributes for the unlock_gate effect are:

- selected_object_ids

### LOCK_GATE        = <EffectId.LOCK_GATE: 7>
Attributes for the lock_gate effect are:

- selected_object_ids

### ACTIVATE_TRIGGER        = <EffectId.ACTIVATE_TRIGGER: 8>
Attributes for the activate_trigger effect are:

- trigger_id

### DEACTIVATE_TRIGGER        = <EffectId.DEACTIVATE_TRIGGER: 9>
Attributes for the deactivate_trigger effect are:

- trigger_id

### AI_SCRIPT_GOAL        = <EffectId.AI_SCRIPT_GOAL: 10>
Attributes for the deactivate_trigger effect are:

- ai_script_goal

### CREATE_OBJECT        = <EffectId.CREATE_OBJECT: 11>
Attributes for the create_object effect are:

- object_list_unit_id

- source_player

- location_x

- location_y

- facet

- disable_sound

### TASK_OBJECT        = <EffectId.TASK_OBJECT: 12>
Attributes for the task_object effect are:

- object_list_unit_id

- source_player

- location_x

- location_y

- location_object_reference

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- action_type

- selected_object_ids

- disable_garrison_unload_sound

- max_units_affected

- issue_group_command

- queue_action

### DECLARE_VICTORY        = <EffectId.DECLARE_VICTORY: 13>
Attributes for the declare_victory effect are:

- source_player

- enabled

### KILL_OBJECT        = <EffectId.KILL_OBJECT: 14>
Attributes for the kill_object effect are:

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- selected_object_ids

- max_units_affected

### REMOVE_OBJECT        = <EffectId.REMOVE_OBJECT: 15>
Attributes for the remove_object effect are:

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- object_state

- selected_object_ids

- max_units_affected

### CHANGE_VIEW        = <EffectId.CHANGE_VIEW: 16>
Attributes for the change_view effect are:

- quantity

- source_player

- location_x

- location_y

- scroll

### UNLOAD        = <EffectId.UNLOAD: 17>
Attributes for the unload effect are:

- object_list_unit_id

- source_player

- location_x

- location_y

- location_object_reference

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- selected_object_ids

- max_units_affected

### CHANGE_OWNERSHIP        = <EffectId.CHANGE_OWNERSHIP: 18>
Attributes for the change_ownership effect are:

- object_list_unit_id

- source_player

- target_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- flash_object

- selected_object_ids

- max_units_affected

### PATROL        = <EffectId.PATROL: 19>
Attributes for the patrol effect are:

- object_list_unit_id

- source_player

- location_x

- location_y

- location_object_reference

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- selected_object_ids

- max_units_affected

### DISPLAY_INSTRUCTIONS        = <EffectId.DISPLAY_INSTRUCTIONS: 20>
Attributes for the display_instructions effect are:

- object_list_unit_id

- source_player

- string_id

- display_time

- instruction_panel_position

- play_sound

- message

- sound_name

- use_tag_color_for_icon

### CLEAR_INSTRUCTIONS        = <EffectId.CLEAR_INSTRUCTIONS: 21>
Attributes for the clear_instructions effect are:

- instruction_panel_position

### FREEZE_OBJECT        = <EffectId.FREEZE_OBJECT: 22>
Attributes for the freeze_object effect are:

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- selected_object_ids

- max_units_affected

### USE_ADVANCED_BUTTONS        = <EffectId.USE_ADVANCED_BUTTONS: 23>
Attributes for the use_advanced_buttons effect are:

None.

Please don't use this effect. Please.

### DAMAGE_OBJECT        = <EffectId.DAMAGE_OBJECT: 24>
Attributes for the damage_object effect are:

- quantity

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- selected_object_ids

- max_units_affected

### PLACE_FOUNDATION        = <EffectId.PLACE_FOUNDATION: 25>
Attributes for the place_foundation effect are:

- object_list_unit_id

- source_player

- location_x

- location_y

### CHANGE_OBJECT_NAME        = <EffectId.CHANGE_OBJECT_NAME: 26>
Attributes for the change_object_name effect are:

- object_list_unit_id

- source_player

- string_id

- area_x1

- area_y1

- area_x2

- area_y2

- message

- selected_object_ids

- max_units_affected

### CHANGE_OBJECT_HP        = <EffectId.CHANGE_OBJECT_HP: 27>
Attributes for the change_object_hp effect are:

- quantity

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- operation

- selected_object_ids

- max_units_affected

### CHANGE_OBJECT_ATTACK        = <EffectId.CHANGE_OBJECT_ATTACK: 28>
Attributes for the change_object_attack effect are:

- armour_attack_quantity

- armour_attack_class

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- operation

- selected_object_ids

- max_units_affected

### STOP_OBJECT        = <EffectId.STOP_OBJECT: 29>
Attributes for the stop_object effect are:

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- selected_object_ids

- max_units_affected

### ATTACK_MOVE        = <EffectId.ATTACK_MOVE: 30>
Attributes for the attack_move effect are:

- object_list_unit_id

- source_player

- location_x

- location_y

- location_object_reference

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- selected_object_ids

- max_units_affected

### CHANGE_OBJECT_ARMOR        = <EffectId.CHANGE_OBJECT_ARMOR: 31>
Attributes for the change_object_armor effect are:

- armour_attack_quantity

- armour_attack_class

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- operation

- selected_object_ids

- max_units_affected

### CHANGE_OBJECT_RANGE        = <EffectId.CHANGE_OBJECT_RANGE: 32>
Attributes for the change_object_range effect are:

- quantity

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- operation

- selected_object_ids

- max_units_affected

### CHANGE_OBJECT_SPEED        = <EffectId.CHANGE_OBJECT_SPEED: 33>
Attributes for the change_object_speed effect are:

- quantity

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- selected_object_ids

- max_units_affected

### HEAL_OBJECT        = <EffectId.HEAL_OBJECT: 34>
Attributes for the heal_object effect are:

- quantity

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- selected_object_ids

- max_units_affected

### TELEPORT_OBJECT        = <EffectId.TELEPORT_OBJECT: 35>
Attributes for the teleport_object effect are:

- object_list_unit_id

- source_player

- location_x

- location_y

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- selected_object_ids

- max_units_affected

### CHANGE_OBJECT_STANCE        = <EffectId.CHANGE_OBJECT_STANCE: 36>
Attributes for the change_object_stance effect are:

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- attack_stance

- selected_object_ids

- max_units_affected

### DISPLAY_TIMER        = <EffectId.DISPLAY_TIMER: 37>
Attributes for the display_timer effect are:

- string_id

- display_time

- time_unit

- timer

- reset_timer

- message

### ENABLE_DISABLE_OBJECT        = <EffectId.ENABLE_DISABLE_OBJECT: 38>
Attributes for the enable_disable_object effect are:

- object_list_unit_id

- source_player

- enabled

### ENABLE_DISABLE_TECHNOLOGY        = <EffectId.ENABLE_DISABLE_TECHNOLOGY: 39>
Attributes for the enable_disable_technology effect are:

- source_player

- technology

- enabled

### CHANGE_OBJECT_COST        = <EffectId.CHANGE_OBJECT_COST: 40>
Attributes for the change_object_cost effect are:

- object_list_unit_id

- source_player

- resource_1

- resource_1_quantity

- resource_2

- resource_2_quantity

- resource_3

- resource_3_quantity

### SET_PLAYER_VISIBILITY        = <EffectId.SET_PLAYER_VISIBILITY: 41>
Attributes for the set_player_visibility effect are:

- source_player

- target_player

- visibility_state

### CHANGE_OBJECT_ICON        = <EffectId.CHANGE_OBJECT_ICON: 42>
Attributes for the change_object_icon effect are:

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- object_list_unit_id_2

- selected_object_ids

- max_units_affected

### REPLACE_OBJECT        = <EffectId.REPLACE_OBJECT: 43>
Attributes for the replace_object effect are:

- object_list_unit_id

- source_player

- target_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- object_list_unit_id_2

- selected_object_ids

- facet2

- max_units_affected

### CHANGE_OBJECT_DESCRIPTION        = <EffectId.CHANGE_OBJECT_DESCRIPTION: 44>
Attributes for the change_object_description effect are:

- object_list_unit_id

- source_player

- string_id

- message

### CHANGE_PLAYER_NAME        = <EffectId.CHANGE_PLAYER_NAME: 45>
Attributes for the change_player_name effect are:

- source_player

- string_id

- message

### CHANGE_TRAIN_LOCATION        = <EffectId.CHANGE_TRAIN_LOCATION: 46>
Attributes for the change_train_location effect are:

- object_list_unit_id

- source_player

- object_list_unit_id_2

- button_location

### CHANGE_TECHNOLOGY_LOCATION        = <EffectId.CHANGE_TECHNOLOGY_LOCATION: 47>
Attributes for the change_technology_location effect are:

- source_player

- technology

- object_list_unit_id_2

- button_location

### CHANGE_CIVILIZATION_NAME        = <EffectId.CHANGE_CIVILIZATION_NAME: 48>
Attributes for the change_civilization_name effect are:

- source_player

- string_id

- message

### CREATE_GARRISONED_OBJECT        = <EffectId.CREATE_GARRISONED_OBJECT: 49>
Attributes for the create_garrisoned_object effect are:

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_list_unit_id_2

- selected_object_ids

- max_units_affected

- disable_sound

### ACKNOWLEDGE_AI_SIGNAL        = <EffectId.ACKNOWLEDGE_AI_SIGNAL: 50>
Attributes for the acknowledge_ai_signal effect are:

- ai_signal_value

### MODIFY_ATTRIBUTE        = <EffectId.MODIFY_ATTRIBUTE: 51>
Attributes for the modify_attribute effect are:

- quantity

- quantity_float

- object_list_unit_id

- source_player

- operation

- object_attributes

- message

### MODIFY_RESOURCE        = <EffectId.MODIFY_RESOURCE: 52>
Attributes for the modify_resource effect are:

- quantity

- tribute_list

- source_player

- operation

### MODIFY_RESOURCE_BY_VARIABLE        = <EffectId.MODIFY_RESOURCE_BY_VARIABLE: 53>
Attributes for the modify_resource_by_variable effect are:

- tribute_list

- source_player

- operation

- variable

### SET_BUILDING_GATHER_POINT        = <EffectId.SET_BUILDING_GATHER_POINT: 54>
Attributes for the set_building_gather_point effect are:

- object_list_unit_id

- source_player

- location_x

- location_y

- area_x1

- area_y1

- area_x2

- area_y2

- selected_object_ids

- max_units_affected

### SCRIPT_CALL        = <EffectId.SCRIPT_CALL: 55>
Attributes for the script_call effect are:

- string_id

- message

### CHANGE_VARIABLE        = <EffectId.CHANGE_VARIABLE: 56>
Attributes for the change_variable effect are:

- quantity

- operation

- variable

- message

### CLEAR_TIMER        = <EffectId.CLEAR_TIMER: 57>
Attributes for the clear_timer effect are:

- timer

### CHANGE_OBJECT_PLAYER_COLOR        = <EffectId.CHANGE_OBJECT_PLAYER_COLOR: 58>
Attributes for the change_object_player_color effect are:

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- player_color

- selected_object_ids

- max_units_affected

### CHANGE_OBJECT_CIVILIZATION_NAME        = <EffectId.CHANGE_OBJECT_CIVILIZATION_NAME: 59>
Attributes for the change_object_civilization_name effect are:

- string_id

- area_x1

- area_y1

- area_x2

- area_y2

- selected_object_ids

- max_units_affected

### CHANGE_OBJECT_PLAYER_NAME        = <EffectId.CHANGE_OBJECT_PLAYER_NAME: 60>
Attributes for the change_object_player_name effect are:

- object_list_unit_id

- source_player

- string_id

- area_x1

- area_y1

- area_x2

- area_y2

- max_units_affected

- selected_object_ids

### DISABLE_UNIT_TARGETING        = <EffectId.DISABLE_UNIT_TARGETING: 61>
Attributes for the disable_unit_targeting effect are:

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- selected_object_ids

- max_units_affected

### ENABLE_UNIT_TARGETING        = <EffectId.ENABLE_UNIT_TARGETING: 62>
Attributes for the enable_unit_targeting effect are:

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- selected_object_ids

- max_units_affected

### CHANGE_TECHNOLOGY_COST        = <EffectId.CHANGE_TECHNOLOGY_COST: 63>
Attributes for the change_technology_cost effect are:

- source_player

- technology

- resource_1

- resource_1_quantity

- resource_2

- resource_2_quantity

- resource_3

- resource_3_quantity

### CHANGE_TECHNOLOGY_RESEARCH_TIME        = <EffectId.CHANGE_TECHNOLOGY_RESEARCH_TIME: 64>
Attributes for the change_technology_research_time effect are:

- quantity

- source_player

- technology

### CHANGE_TECHNOLOGY_NAME        = <EffectId.CHANGE_TECHNOLOGY_NAME: 65>
Attributes for the change_technology_name effect are:

- source_player

- technology

- string_id

- message

### CHANGE_TECHNOLOGY_DESCRIPTION        = <EffectId.CHANGE_TECHNOLOGY_DESCRIPTION: 66>
Attributes for the change_technology_description effect are:

- source_player

- technology

- string_id

- message

### ENABLE_TECHNOLOGY_STACKING        = <EffectId.ENABLE_TECHNOLOGY_STACKING: 67>
Attributes for the enable_technology_stacking effect are:

- source_player

- technology

### DISABLE_TECHNOLOGY_STACKING        = <EffectId.DISABLE_TECHNOLOGY_STACKING: 68>
Attributes for the disable_technology_stacking effect are:

- source_player

- technology

### ACKNOWLEDGE_MULTIPLAYER_AI_SIGNAL        = <EffectId.ACKNOWLEDGE_MULTIPLAYER_AI_SIGNAL: 69>
Attributes for the acknowledge_multiplayer_ai_signal effect are:

- ai_signal_value

### DISABLE_OBJECT_SELECTION        = <EffectId.DISABLE_OBJECT_SELECTION: 70>
Attributes for the disable_object_selection effect are:

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- selected_object_ids

- max_units_affected

### ENABLE_OBJECT_SELECTION        = <EffectId.ENABLE_OBJECT_SELECTION: 71>
Attributes for the enable_object_selection effect are:

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- selected_object_ids

- max_units_affected

### CHANGE_COLOR_MOOD        = <EffectId.CHANGE_COLOR_MOOD: 72>
Attributes for the change_color_mood effect are:

- quantity

- color_mood

This effect was added in: 1.42

### ENABLE_OBJECT_DELETION        = <EffectId.ENABLE_OBJECT_DELETION: 73>
Attributes for the enable_object_deletion effect are:

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- selected_object_ids

- max_units_affected

This effect was added in: 1.46

### DISABLE_OBJECT_DELETION        = <EffectId.DISABLE_OBJECT_DELETION: 74>
Attributes for the disable_object_deletion effect are:

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- selected_object_ids

- max_units_affected

This effect was added in: 1.46

### TRAIN_UNIT        = <EffectId.TRAIN_UNIT: 75>
Attributes for the train_unit effect are:

- quantity

- object_list_unit_id

- source_player

- location_x

- location_y

- area_x1

- area_y1

- area_x2

- area_y2

- selected_object_ids

- max_units_affected

This effect was added in: 1.51 & Trigger Version 3.5

### INITIATE_RESEARCH        = <EffectId.INITIATE_RESEARCH: 76>
Attributes for the initiate_research effect are:

- source_player

- technology

- selected_object_ids

This effect was added in: 1.51 & Trigger Version 3.5

### CREATE_OBJECT_ATTACK        = <EffectId.CREATE_OBJECT_ATTACK: 77>
Attributes for the create_object_attack effect are:

- armour_attack_quantity

- armour_attack_class

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- operation

- selected_object_ids

- max_units_affected

This effect was added in: 1.51 & Trigger Version 3.5

### CREATE_OBJECT_ARMOR        = <EffectId.CREATE_OBJECT_ARMOR: 78>
Attributes for the create_object_armor effect are:

- armour_attack_quantity

- armour_attack_class

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- object_type

- operation

- selected_object_ids

- max_units_affected

This effect was added in: 1.51 & Trigger Version 3.5

### MODIFY_ATTRIBUTE_BY_VARIABLE        = <EffectId.MODIFY_ATTRIBUTE_BY_VARIABLE: 79>
Attributes for the modify_attribute_by_variable effect are:

- object_list_unit_id

- source_player

- operation

- object_attributes

- variable

- message

- armour_attack_class

This effect was added in: 1.51 & Trigger Version 3.5

### SET_OBJECT_COST        = <EffectId.SET_OBJECT_COST: 80>
Attributes for the set_object_cost effect are:

- object_list_unit_id

- source_player

- quantity

- tribute_list

This effect was added in: 1.54 & Trigger Version 3.9

### LOAD_KEY_VALUE        = <EffectId.LOAD_KEY_VALUE: 81>
Attributes for the load_key_value effect are:

- variable

- message

- quantity

This effect was added in: 1.54 & Trigger Version 3.9

### STORE_KEY_VALUE        = <EffectId.STORE_KEY_VALUE: 82>
Attributes for the store_key_value effect are:

- variable

- message

This effect was added in: 1.54 & Trigger Version 3.9

### DELETE_KEY        = <EffectId.DELETE_KEY: 83>
Attributes for the delete_key effect are:

- message

This effect was added in: 1.54 & Trigger Version 3.9

### CHANGE_TECHNOLOGY_ICON        = <EffectId.CHANGE_TECHNOLOGY_ICON: 84>
Attributes for the change_technology_icon effect are:

- technology

- source_player

- quantity

This effect was added in: 1.54 & Trigger Version 3.9

### CHANGE_TECHNOLOGY_HOTKEY        = <EffectId.CHANGE_TECHNOLOGY_HOTKEY: 85>
Attributes for the change_technology_hotkey effect are:

- technology

- source_player

- quantity

This effect was added in: 1.54 & Trigger Version 3.9

### MODIFY_VARIABLE_BY_RESOURCE        = <EffectId.MODIFY_VARIABLE_BY_RESOURCE: 86>
Attributes for the modify_variable_by_resource effect are:

- tribute_list

- source_player

- operation

- variable

This effect was added in: 1.54 & Trigger Version 3.9

### MODIFY_VARIABLE_BY_ATTRIBUTE        = <EffectId.MODIFY_VARIABLE_BY_ATTRIBUTE: 87>
Attributes for the modify_variable_by_attribute effect are:

- object_list_unit_id

- source_player

- operation

- object_attributes

- variable

- message

- armour_attack_class

This effect was added in: 1.54 & Trigger Version 3.9

### CHANGE_OBJECT_CAPTION        = <EffectId.CHANGE_OBJECT_CAPTION: 88>
Attributes for the change_object_caption effect are:

- object_list_unit_id

- source_player

- string_id

- message

- selected_object_ids

- area_x1

- area_y1

- area_x2

- area_y2

This effect was added in: 1.54 & Trigger Version 3.9

### CHANGE_PLAYER_COLOR        = <EffectId.CHANGE_PLAYER_COLOR: 89>
Attributes for the change_player_color effect are:

- source_player

- player_color

This effect was added in: 1.54 & Trigger Version 3.9

### CREATE_DECISION        = <EffectId.CREATE_DECISION: 90>
Attributes for the create_decision effect are:

- string_id

- decision_id

- string_id_option1

- string_id_option2

- message

- message_option1

- message_option2

This effect was added in: 1.54 & Trigger Version 4.1

### DISABLE_UNIT_ATTACKABLE        = <EffectId.DISABLE_UNIT_ATTACKABLE: 98>
Attributes for the disable_unit_attackable effect are:

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- selected_object_ids

- max_units_affected

This effect was added in: 1.54 & Trigger Version 4.1

### ENABLE_UNIT_ATTACKABLE        = <EffectId.ENABLE_UNIT_ATTACKABLE: 99>
Attributes for the enable_unit_attackable effect are:

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- selected_object_ids

- max_units_affected

This effect was added in: 1.54 & Trigger Version 4.1

### MODIFY_VARIABLE_BY_VARIABLE        = <EffectId.MODIFY_VARIABLE_BY_VARIABLE: 100>
Attributes for the modify_variable_by_variable effect are:

- operation

- variable

- variable2

This effect was added in: 1.54 & Trigger Version 4.1

### COUNT_UNITS_INTO_VARIABLE        = <EffectId.COUNT_UNITS_INTO_VARIABLE: 101>
Attributes for the count_units_into_variable effect are:

- object_list_unit_id

- source_player

- area_x1

- area_y1

- area_x2

- area_y2

- object_group

- variable2  // Why FE?! Why the 2nd!?

This effect was added in: 1.54 & Trigger Version 4.1

### ADD_TRAIN_LOCATION        = <EffectId.ADD_TRAIN_LOCATION: 102>
Attributes for the add_train_location effect are:

- object_list_unit_id

- source_player

- object_list_unit_id_2

- button_location

- train_time

- hotkey

This effect was added in: 1.55 & Trigger Version 4.5

### RESEARCH_LOCAL_TECHNOLOGY        = <EffectId.RESEARCH_LOCAL_TECHNOLOGY: 103>
Attributes for the research_local_technology effect are:

- local_technology

- source_player

- selected_object_ids

- area_x1

- area_y1

- area_x2

- area_y2

- object_list_unit_id_2

This effect was added in: 1.55 & Trigger Version 4.5

### MODIFY_ATTRIBUTE_FOR_CLASS        = <EffectId.MODIFY_ATTRIBUTE_FOR_CLASS: 104>
Attributes for the modify_attribute_for_class effect are:

- object_group2

- source_player

- object_attributes

- message

- operation

- quantity

- quantity_float

- armour_attack_class

This effect was added in: 1.55 & Trigger Version 4.5

### MODIFY_OBJECT_ATTRIBUTE        = <EffectId.MODIFY_OBJECT_ATTRIBUTE: 105>
Attributes for the modify_object_attribute effect are:

- object_list_unit_id

- source_player

- object_attributes

- selected_object_ids

- area_x1

- area_y1

- area_x2

- area_y2

- operation

- message

- quantity

- quantity_float

- armour_attack_class

- object_filter

This effect was added in: 1.55 & Trigger Version 4.5

### MODIFY_OBJECT_ATTRIBUTE_BY_VARIABLE        = <EffectId.MODIFY_OBJECT_ATTRIBUTE_BY_VARIABLE: 106>
Attributes for the modify_object_attribute_by_variable effect are:

- object_list_unit_id

- source_player

- object_attributes

- selected_object_ids

- area_x1

- area_y1

- area_x2

- area_y2

- operation

- message

- variable

- armour_attack_class

This effect was added in: 1.55 & Trigger Version 4.5

### CHANGE_OBJECT_VISIBILITY        = <EffectId.CHANGE_OBJECT_VISIBILITY: 107>
Attributes for the change_object_visibility effect are:

- source_player

- target_player

- area_x1

- area_y1

- area_x2

- area_y2

- visibility_state

- max_units_affected

- selected_object_ids

This effect was added in: 1.55 & Trigger Version 4.5

### BUILD_OBJECT        = <EffectId.BUILD_OBJECT: 108>
Attributes for the build_object effect are:

- object_list_unit_id

- source_player

- location_x

- location_y

- location_object_reference

- area_x1

- area_y1

- area_x2

- area_y2

- wall_x1

- wall_y1

- wall_x2

- wall_y2

- object_group

- object_type

- building_list

- selected_object_ids

- disable_garrison_unload_sound

- max_units_affected

- issue_group_command

- queue_action

This effect was added in: 1.57 & Trigger Version 4.6

### MIRROR_DIPLOMACY        = <EffectId.MIRROR_DIPLOMACY: 109>
Attributes for the mirror_diplomacy effect are:

- source_player

- target_player

- enabled

This effect was added in: 1.57 & Trigger Version 4.6


### class     HeroInfo(AoE2ScenarioParser.datasets.support.info_dataset_base.InfoDatasetBase):
This enum class provides information about most of the heroes in the game. Information about the following
properties of a hero is found in this class:

- Unit ID

- Icon ID

- Dead Unit ID

- HotKey ID

- If the hero is a gaia only unit

Inherited Methods from class InfoDatasetBase

Examples

### @staticmethod
Args:
    include_chronicles: if set to True, include chronicles heroes

Returns:
    A list of all trainable heroes

### KHOSRAU        = <HeroInfo.KHOSRAU: (1297, 172, 1667, 16311, False)>

### LEIF_ERIKSON        = <HeroInfo.LEIF_ERIKSON: (106, 118, -1, 16457, False)>

### RICHARD_THE_LIONHEART        = <HeroInfo.RICHARD_THE_LIONHEART: (160, 92, 570, 16633, False)>

### THE_BLACK_PRINCE        = <HeroInfo.THE_BLACK_PRINCE: (161, 343, 139, 16622, False)>

### FRIAR_TUCK        = <HeroInfo.FRIAR_TUCK: (163, 311, 134, 16626, False)>

### SHERIFF_OF_NOTTINGHAM        = <HeroInfo.SHERIFF_OF_NOTTINGHAM: (164, 182, 180, 16635, False)>

### CHARLEMAGNE        = <HeroInfo.CHARLEMAGNE: (165, 160, 157, 16623, False)>

### ROLAND        = <HeroInfo.ROLAND: (166, 320, 111, 16634, False)>

### BELISARIUS        = <HeroInfo.BELISARIUS: (167, 187, 277, 16621, False)>

### THEODORIC_THE_GOTH        = <HeroInfo.THEODORIC_THE_GOTH: (168, 163, 62, 16638, False)>

### AETHELFRITH        = <HeroInfo.AETHELFRITH: (169, 161, 233, 16619, False)>

### SIEGFRIED        = <HeroInfo.SIEGFRIED: (170, 301, 568, 16636, False)>

### ERIK_THE_RED        = <HeroInfo.ERIK_THE_RED: (171, 118, 693, 16625, False)>

### TAMERLANE        = <HeroInfo.TAMERLANE: (172, 261, 135, 16637, False)>

### KING_ARTHUR        = <HeroInfo.KING_ARTHUR: (173, 301, 568, 16628, False)>

### LANCELOT        = <HeroInfo.LANCELOT: (174, 305, 570, 16630, False)>

### GAWAIN        = <HeroInfo.GAWAIN: (175, 343, 139, 16627, False)>

### MORDRED        = <HeroInfo.MORDRED: (176, 305, 570, 16632, False)>

### ARCHBISHOP        = <HeroInfo.ARCHBISHOP: (177, 311, 134, 16620, False)>

### VLAD_DRACULA        = <HeroInfo.VLAD_DRACULA: (193, 147, 1617, 16101, False)>

### KITABATAKE        = <HeroInfo.KITABATAKE: (195, 307, 151, 16629, False)>

### MINAMOTO        = <HeroInfo.MINAMOTO: (196, 126, 151, 16631, False)>

### ALEXANDER_NEVSKI        = <HeroInfo.ALEXANDER_NEVSKI: (197, 75, 139, 16639, False)>

### EL_CID        = <HeroInfo.EL_CID: (198, 173, 568, 16624, False)>

### ROBIN_HOOD        = <HeroInfo.ROBIN_HOOD: (200, 326, 115, 16640, False)>

### VASCO_DA_GAMA        = <HeroInfo.VASCO_DA_GAMA: (203, 167, -1, 16106, False)>

### ALARIC_THE_GOTH        = <HeroInfo.ALARIC_THE_GOTH: (223, 163, 1620, 16638, False)>

### KING_BELA_IV        = <HeroInfo.KING_BELA_IV: (230, 323, 497, 16738, False)>

### CUAUHTEMOC        = <HeroInfo.CUAUHTEMOC: (307, 146, 1117, 16673, False)>

### HENRY_THE_LION        = <HeroInfo.HENRY_THE_LION: (418, 328, 111, 16531, False)>

### CHARLES_MARTEL        = <HeroInfo.CHARLES_MARTEL: (424, 129, 157, 16291, False)>

### FRANCISCO_DE_ORELLANA        = <HeroInfo.FRANCISCO_DE_ORELLANA: (425, 153, 772, 16689, False)>

### HARALD_HARDRADA        = <HeroInfo.HARALD_HARDRADA: (426, 923, 693, 16293, False)>

### GONZALO_PIZARRO        = <HeroInfo.GONZALO_PIZARRO: (427, 167, 772, 16689, False)>

### HROLF_THE_GANGER        = <HeroInfo.HROLF_THE_GANGER: (428, 302, 693, 16295, False)>

### FREDERICK_BARBAROSSA        = <HeroInfo.FREDERICK_BARBAROSSA: (429, 154, 181, 16462, False)>

### JOAN_THE_MAID        = <HeroInfo.JOAN_THE_MAID: (430, 52, 431, 16297, False)>

### WILLIAM_WALLACE        = <HeroInfo.WILLIAM_WALLACE: (432, 363, 433, 16299, False)>

### PRITHVIRAJ        = <HeroInfo.PRITHVIRAJ: (437, 176, 1627, 16412, False)>

### FRANCESCO_SFORZA        = <HeroInfo.FRANCESCO_SFORZA: (439, 162, 1615, 16679, False)>

### ATAULF        = <HeroInfo.ATAULF: (453, 163, 1624, 16638, False)>

### JOAN_OF_ARC        = <HeroInfo.JOAN_OF_ARC: (629, 76, 630, 16526, False)>

### FRANKISH_PALADIN        = <HeroInfo.FRANKISH_PALADIN: (632, 62, 633, 16529, False)>

### SIEUR_DE_METZ        = <HeroInfo.SIEUR_DE_METZ: (634, 59, 111, 16531, False)>

### SIEUR_BERTRAND        = <HeroInfo.SIEUR_BERTRAND: (636, 61, 111, 16533, False)>

### DUKE_D_ALENCON        = <HeroInfo.DUKE_D_ALENCON: (638, 65, 633, 16535, False)>

### LA_HIRE        = <HeroInfo.LA_HIRE: (640, 51, 568, 16537, False)>

### LORD_DE_GRAVILLE        = <HeroInfo.LORD_DE_GRAVILLE: (642, 66, 496, 16539, False)>

### JEAN_DE_LORRAIN        = <HeroInfo.JEAN_DE_LORRAIN: (644, 67, 16, 16541, False)>

### CONSTABLE_RICHEMONT        = <HeroInfo.CONSTABLE_RICHEMONT: (646, 343, 633, 16543, False)>

### GUY_JOSSELYNE        = <HeroInfo.GUY_JOSSELYNE: (648, 56, 570, 16545, False)>

### JEAN_BUREAU        = <HeroInfo.JEAN_BUREAU: (650, 68, 16, 16547, False)>

### SIR_JOHN_FASTOLF        = <HeroInfo.SIR_JOHN_FASTOLF: (652, 69, 633, 16549, False)>

### REYNALD_DE_CHATILLON        = <HeroInfo.REYNALD_DE_CHATILLON: (678, 70, 633, 16560, False)>

### MASTER_OF_THE_TEMPLAR        = <HeroInfo.MASTER_OF_THE_TEMPLAR: (680, 75, 633, 16562, False)>

### BAD_NEIGHBOR        = <HeroInfo.BAD_NEIGHBOR: (682, 94, 194, 16564, False)>

### GODS_OWN_SLING        = <HeroInfo.GODS_OWN_SLING: (683, 94, 194, 16565, False)>

### ARCHER_OF_THE_EYES        = <HeroInfo.ARCHER_OF_THE_EYES: (686, 77, 687, 16568, False)>

### SUBOTAI        = <HeroInfo.SUBOTAI: (698, 53, 1618, 16580, False)>

### HUNTING_WOLF        = <HeroInfo.HUNTING_WOLF: (700, 7, 237, 16582, False)>

### KUSHLUK        = <HeroInfo.KUSHLUK: (702, 81, 1638, 16584, False)>

### TOPA_YUPANQUI        = <HeroInfo.TOPA_YUPANQUI: (703, 327, 750, 16669, False)>

### SHAH        = <HeroInfo.SHAH: (704, 82, 1337, 16586, False)>

### SABOTEUR        = <HeroInfo.SABOTEUR: (706, 58, -1, 16588, False)>

### ORNLU_THE_WOLF        = <HeroInfo.ORNLU_THE_WOLF: (707, 145, 708, 16589, False)>

### GODS_OWN_SLING_PACKED        = <HeroInfo.GODS_OWN_SLING_PACKED: (729, 313, 735, 16611, False)>

### BAD_NEIGHBOR_PACKED        = <HeroInfo.BAD_NEIGHBOR_PACKED: (730, 313, 735, 16612, False)>

### GENGHIS_KHAN        = <HeroInfo.GENGHIS_KHAN: (731, 54, 135, 16613, False)>

### EMPEROR_IN_A_BARREL        = <HeroInfo.EMPEROR_IN_A_BARREL: (733, 57, 1666, 16615, False)>

### CUSI_YUPANQUI        = <HeroInfo.CUSI_YUPANQUI: (749, 306, 1626, 16671, False)>

### ATTILA_THE_HUN        = <HeroInfo.ATTILA_THE_HUN: (777, 119, 1619, 16695, False)>

### BLEDA_THE_HUN        = <HeroInfo.BLEDA_THE_HUN: (779, 120, 1371, 16697, False)>

### POPE_LEO_I        = <HeroInfo.POPE_LEO_I: (781, 130, 134, 16699, False)>

### SCYTHIAN_WILD_WOMAN        = <HeroInfo.SCYTHIAN_WILD_WOMAN: (783, 121, 431, 16701, False)>

### EL_CID_CAMPEADOR        = <HeroInfo.EL_CID_CAMPEADOR: (824, 173, 633, 16724, False)>

### KING_SANCHO        = <HeroInfo.KING_SANCHO: (838, 124, 497, 16738, False)>

### KING_ALFONSO        = <HeroInfo.KING_ALFONSO: (840, 123, 497, 16740, False)>

### IMAM        = <HeroInfo.IMAM: (842, 324, 1326, 16742, False)>

### ADMIRAL_YI_SUN_SHIN        = <HeroInfo.ADMIRAL_YI_SUN_SHIN: (844, 127, -1, 16744, False)>

### NOBUNAGA        = <HeroInfo.NOBUNAGA: (845, 126, 151, 16745, False)>

### HENRY_V        = <HeroInfo.HENRY_V: (847, 125, 570, 16747, False)>

### WILLIAM_THE_CONQUEROR        = <HeroInfo.WILLIAM_THE_CONQUEROR: (849, 128, 633, 16749, False)>

### SCYTHIAN_SCOUT        = <HeroInfo.SCYTHIAN_SCOUT: (852, 321, 547, 16752, False)>

### MUSA_IBN_NUSAYR        = <HeroInfo.MUSA_IBN_NUSAYR: (1034, 204, 1008, 16101, False)>

### SUNDJATA        = <HeroInfo.SUNDJATA: (1035, 206, 1395, 16777, False)>

### TARIQ_IBN_ZIYAD        = <HeroInfo.TARIQ_IBN_ZIYAD: (1036, 207, 1616, 16415, False)>

### RICHARD_DE_CLARE        = <HeroInfo.RICHARD_DE_CLARE: (1037, 210, 547, 16778, False)>

### TRISTAN        = <HeroInfo.TRISTAN: (1038, 322, 870, 16779, False)>

### PRINCESS_YODIT        = <HeroInfo.PRINCESS_YODIT: (1039, 216, 1328, 16781, False)>

### HENRY_II        = <HeroInfo.HENRY_II: (1040, 325, 500, 16780, False)>

### YEKUNO_AMLAK        = <HeroInfo.YEKUNO_AMLAK: (1064, 208, 1017, 16799, False)>

### YODIT        = <HeroInfo.YODIT: (1066, 216, 1625, 16220, False)>

### ITZCOATL        = <HeroInfo.ITZCOATL: (1067, 317, 750, 16206, False)>

### MUSTAFA_PASHA        = <HeroInfo.MUSTAFA_PASHA: (1068, 318, 107, 16207, False)>

### PACAL_II        = <HeroInfo.PACAL_II: (1069, 314, 764, 16208, False)>

### BABUR        = <HeroInfo.BABUR: (1070, 316, 300, 16209, False)>

### ABRAHA_ELEPHANT        = <HeroInfo.ABRAHA_ELEPHANT: (1071, 310, 136, 16210, False)>

### GUGLIELMO_EMBRIACO        = <HeroInfo.GUGLIELMO_EMBRIACO: (1072, 312, 867, 16211, False)>

### SU_DINGFANG        = <HeroInfo.SU_DINGFANG: (1073, 137, 28, 16212, False)>

### PACHACUTI        = <HeroInfo.PACHACUTI: (1074, 319, 1633, 16213, False)>

### HUAYNA_CAPAC        = <HeroInfo.HUAYNA_CAPAC: (1075, 308, 186, 16214, False)>

### MIKLOS_TOLDI        = <HeroInfo.MIKLOS_TOLDI: (1076, 100, 870, 16215, False)>

### LITTLE_JOHN        = <HeroInfo.LITTLE_JOHN: (1077, 309, 140, 16216, False)>

### ZAWISZA_THE_BLACK        = <HeroInfo.ZAWISZA_THE_BLACK: (1078, 384, 480, 16217, False)>

### SUMANGURU        = <HeroInfo.SUMANGURU: (1080, 205, 1621, 16218, False)>

### DAGNAJAN        = <HeroInfo.DAGNAJAN: (1106, 209, 1108, 16232, False)>

### GIDAJAN        = <HeroInfo.GIDAJAN: (1109, 245, 1110, 16101, False)>

### GAJAH_MADA        = <HeroInfo.GAJAH_MADA: (1157, 220, 1190, 16469, False)>

### JAYANEGARA        = <HeroInfo.JAYANEGARA: (1158, 342, 732, 16301, False)>

### RADEN_WIJAYA        = <HeroInfo.RADEN_WIJAYA: (1159, 222, 139, 16070, False)>

### SUNDA_ROYAL_FIGHTER        = <HeroInfo.SUNDA_ROYAL_FIGHTER: (1160, 234, 1161, 16101, False)>

### SURYAVARMAN_I        = <HeroInfo.SURYAVARMAN_I: (1162, 239, 1154, 16459, False)>

### UDAYADITYAVARMAN_I        = <HeroInfo.UDAYADITYAVARMAN_I: (1163, 241, 732, 16301, False)>

### JAYAVIRAVARMAN        = <HeroInfo.JAYAVIRAVARMAN: (1164, 221, 1124, 16101, False)>

### BAYINNAUNG        = <HeroInfo.BAYINNAUNG: (1165, 219, 1637, 16459, False)>

### TABINSHWEHTI        = <HeroInfo.TABINSHWEHTI: (1166, 223, 1667, 16101, False)>

### LE_LOI        = <HeroInfo.LE_LOI: (1178, 243, 1623, 16299, False)>

### LE_LAI        = <HeroInfo.LE_LAI: (1180, 242, 1224, 16633, False)>

### LE_TRIEN        = <HeroInfo.LE_TRIEN: (1181, 237, 568, 16299, False)>

### LUU_NHAN_CHU        = <HeroInfo.LUU_NHAN_CHU: (1182, 238, 687, 16568, False)>

### BUI_BI        = <HeroInfo.BUI_BI: (1183, 235, 1329, 16742, False)>

### DINH_LE        = <HeroInfo.DINH_LE: (1184, 236, 1224, 16633, False)>

### WANG_TONG        = <HeroInfo.WANG_TONG: (1185, 240, 1224, 16218, False)>

### ENVOY        = <HeroInfo.ENVOY: (1186, 244, 1636, 16777, False)>

### TOKHTAMYSH_KHAN        = <HeroInfo.TOKHTAMYSH_KHAN: (1262, 152, 1229, 16101, False)>

### IVAYLO        = <HeroInfo.IVAYLO: (1265, 257, 1629, 16101, False)>

### TSAR_KONSTANTIN        = <HeroInfo.TSAR_KONSTANTIN: (1266, 254, 1286, 16101, False)>

### KOTYAN_KHAN        = <HeroInfo.KOTYAN_KHAN: (1267, 259, 1287, 16580, False)>

### CUMAN_CHIEF        = <HeroInfo.CUMAN_CHIEF: (1268, 255, 1288, 16533, False)>

### GIRGEN_KHAN        = <HeroInfo.GIRGEN_KHAN: (1269, 256, 1289, 16085, False)>

### URUS_KHAN        = <HeroInfo.URUS_KHAN: (1276, 262, 1232, 16108, False)>

### VYTAUTAS_THE_GREAT        = <HeroInfo.VYTAUTAS_THE_GREAT: (1281, 260, 1278, 16405, False)>

### IVAYLO_DISMOUNTED        = <HeroInfo.IVAYLO_DISMOUNTED: (1290, 257, 1630, 16101, False)>

### SANYOGITA        = <HeroInfo.SANYOGITA: (1293, 170, 1328, 16307, False)>

### PRITHVI        = <HeroInfo.PRITHVI: (1294, 304, 26, 16308, False)>

### CHAND_BARDAI        = <HeroInfo.CHAND_BARDAI: (1295, 171, 1329, 16742, False)>

### SALADIN        = <HeroInfo.SALADIN: (1296, 175, 44, 16453, False)>

### NORSE_CHIEFTAIN        = <HeroInfo.NORSE_CHIEFTAIN: (1298, 188, 1628, 16416, False)>

### OSMAN        = <HeroInfo.OSMAN: (1303, 180, 1632, 16412, False)>

### SOSSO_GUARD        = <HeroInfo.SOSSO_GUARD: (1574, 350, 1575, 16101, False)>

### THE_MIDDLEBROOK        = <HeroInfo.THE_MIDDLEBROOK: (1631, 353, -1, 16457, False)>

### EDWARD_LONGSHANKS        = <HeroInfo.EDWARD_LONGSHANKS: (1669, 358, 1670, 16724, False)>

### GILBERT_DE_CLARE        = <HeroInfo.GILBERT_DE_CLARE: (1671, 364, 1672, 16724, False)>

### JOHN_THE_FEARLESS        = <HeroInfo.JOHN_THE_FEARLESS: (1673, 359, 1674, 16724, False)>

### PHILIP_THE_GOOD        = <HeroInfo.PHILIP_THE_GOOD: (1675, 360, 1676, 16724, False)>

### ROBERT_GUISCARD        = <HeroInfo.ROBERT_GUISCARD: (1677, 361, 1678, 16724, False)>

### ROGER_BOSSO        = <HeroInfo.ROGER_BOSSO: (1679, 362, 1680, 16724, False)>

### BOHEMOND        = <HeroInfo.BOHEMOND: (1681, 357, 1682, 16724, False)>

### LLYWELYN_AP_GRUFFYDD        = <HeroInfo.LLYWELYN_AP_GRUFFYDD: (1683, 368, 1684, 16619, False)>

### DAFYDD_AP_GRUFFYDD        = <HeroInfo.DAFYDD_AP_GRUFFYDD: (1685, 366, 1686, 16619, False)>

### BERNARD_D_ARMAGNAC        = <HeroInfo.BERNARD_D_ARMAGNAC: (1687, 365, 1688, 16724, False)>

### WARWOLF_TREBUCHET        = <HeroInfo.WARWOLF_TREBUCHET: (1690, 94, 194, 16097, False)>

### WARWOLF_TREBUCHET_PACKED        = <HeroInfo.WARWOLF_TREBUCHET_PACKED: (1691, 313, 735, 16381, False)>

### JACQUELINE_OF_HAINAUT        = <HeroInfo.JACQUELINE_OF_HAINAUT: (1692, 367, 1328, 16307, False)>

### STOERTEBEKER        = <HeroInfo.STOERTEBEKER: (114, 88, -1, 16703, False)>

### JAN_ZIZKA        = <HeroInfo.JAN_ZIZKA: (1713, 373, 1714, 16724, False)>

### JADWIGA        = <HeroInfo.JADWIGA: (1715, 374, 1716, 16691, False)>

### JOGAILA        = <HeroInfo.JOGAILA: (1718, 375, 1719, 16724, False)>

### KESTUTIS        = <HeroInfo.KESTUTIS: (1721, 376, 1722, 16724, False)>

### ALGIRDAS        = <HeroInfo.ALGIRDAS: (1725, 378, 1726, 16724, False)>

### ULRICH_VON_JUNGINGEN        = <HeroInfo.ULRICH_VON_JUNGINGEN: (1727, 379, 1728, 16562, False)>

### EMPEROR_SIGISMUND        = <HeroInfo.EMPEROR_SIGISMUND: (1729, 380, 633, 16562, False)>

### DMITRY_OF_MOSCOW        = <HeroInfo.DMITRY_OF_MOSCOW: (1730, 381, 139, 16639, False)>

### MIKHAIL_OF_TVER        = <HeroInfo.MIKHAIL_OF_TVER: (1731, 382, 877, 16639, False)>

### YOUNG_JADWIGA        = <HeroInfo.YOUNG_JADWIGA: (1732, 383, 431, 16297, False)>

### MIHIRA_BHOJA        = <HeroInfo.MIHIRA_BHOJA: (1762, 396, 1752, 16779, False)>

### AMOGHAVARSHA        = <HeroInfo.AMOGHAVARSHA: (1763, 397, 1736, 16779, False)>

### RAJENDRA_CHOLA        = <HeroInfo.RAJENDRA_CHOLA: (1764, 398, 1765, 16633, False)>

### GENERAL_ARAIYAN        = <HeroInfo.GENERAL_ARAIYAN: (1766, 399, 1767, 16218, False)>

### YOUNG_BABUR        = <HeroInfo.YOUNG_BABUR: (1768, 400, 495, 16218, False)>

### QUTLUGH        = <HeroInfo.QUTLUGH: (1769, 401, 1770, 16637, False)>

### IBRAHIM_LODI        = <HeroInfo.IBRAHIM_LODI: (1771, 402, 1277, 16458, False)>

### SHAYBANI_KHAN        = <HeroInfo.SHAYBANI_KHAN: (1772, 403, 1289, 16458, False)>

### SHAH_ISMAIL        = <HeroInfo.SHAH_ISMAIL: (1815, 411, 1816, 16639, False)>

### SELIM_THE_GRIM        = <HeroInfo.SELIM_THE_GRIM: (1820, 419, 1814, 16471, False)>

### THOROS        = <HeroInfo.THOROS: (1821, 413, 1848, 16639, False)>

### TAMAR        = <HeroInfo.TAMAR: (1822, 414, 1823, 16691, False)>

### YURY        = <HeroInfo.YURY: (1824, 421, 1630, 16101, False)>

### IVANE        = <HeroInfo.IVANE: (1825, 417, 27, 16471, False)>

### ZAKARE        = <HeroInfo.ZAKARE: (1826, 422, 1812, 16691, False)>

### STEPHAN        = <HeroInfo.STEPHAN: (1827, 420, 1812, 16691, False)>

### MLEH        = <HeroInfo.MLEH: (1828, 418, 568, 16537, False)>

### POLEMARCH        = <HeroInfo.POLEMARCH: (2162, 622, 2163, 416014, False)>

### POLEMARCH_2        = <HeroInfo.POLEMARCH_2: (2164, 622, 2163, 416014, False)>

### POLEMARCH_3        = <HeroInfo.POLEMARCH_3: (2165, 622, 2163, 416014, False)>

### POLEMARCH_4        = <HeroInfo.POLEMARCH_4: (2166, 622, 2163, 416014, False)>

### POLEMARCH_3_WITH_EPHORATE        = <HeroInfo.POLEMARCH_3_WITH_EPHORATE: (2167, 622, 2163, 416014, False)>

### POLEMARCH_4_WITH_EPHORATE        = <HeroInfo.POLEMARCH_4_WITH_EPHORATE: (2270, 622, 2163, 416014, False)>

### POLEMARCH_3_WITH_MORAI        = <HeroInfo.POLEMARCH_3_WITH_MORAI: (2171, 622, 2163, 416014, False)>

### POLEMARCH_4_WITH_MORAI        = <HeroInfo.POLEMARCH_4_WITH_MORAI: (2272, 622, 2163, 416014, False)>

### ARTAPHERNES        = <HeroInfo.ARTAPHERNES: (2308, 645, 2363, 16412, False)>

### DATIS        = <HeroInfo.DATIS: (2309, 631, 2364, 16444, False)>

### ARISTAGORAS        = <HeroInfo.ARISTAGORAS: (2310, 653, 2370, 16724, False)>

### DIONYSIUS        = <HeroInfo.DIONYSIUS: (2311, 632, -1, 416011, False)>

### ARTEMISIA        = <HeroInfo.ARTEMISIA: (2312, 646, -1, 416008, False)>

### ARISTIDES        = <HeroInfo.ARISTIDES: (2313, 644, 2376, 416013, False)>

### MILTIADES        = <HeroInfo.MILTIADES: (2314, 654, 2163, 16070, False)>

### THEMISTOCLES        = <HeroInfo.THEMISTOCLES: (2315, 642, 2360, 16104, False)>

### LEONIDAS        = <HeroInfo.LEONIDAS: (2316, 634, 2109, 16104, False)>

### BRASIDAS        = <HeroInfo.BRASIDAS: (2317, 648, 2359, 416014, False)>

### LYSANDER        = <HeroInfo.LYSANDER: (2318, 635, 2371, 16104, False)>

### POLYCRITUS        = <HeroInfo.POLYCRITUS: (2319, 640, -1, 416012, False)>

### THEMISTOCLES_WARSHIP        = <HeroInfo.THEMISTOCLES_WARSHIP: (2339, 642, -1, 416008, False)>

### CLEON        = <HeroInfo.CLEON: (2346, 649, 2106, 16104, False)>

### DARIUS        = <HeroInfo.DARIUS: (2347, 651, 2303, -1, False)>

### ISMAIL        = <HeroInfo.ISMAIL: (1819, 416, 449, 16777, False)>

### CAO_CAO        = <HeroInfo.CAO_CAO: (1954, 465, 2, 16381, False)>

### LIU_BEI        = <HeroInfo.LIU_BEI: (1966, 466, 2, 16381, False)>

### SUN_JIAN        = <HeroInfo.SUN_JIAN: (1978, 467, 2, 16381, False)>

### EMPEROR_IN_A_LITTER        = <HeroInfo.EMPEROR_IN_A_LITTER: (1988, 529, -1, 16082, False)>

### LU_BU        = <HeroInfo.LU_BU: (2032, 443, 2, 16533, False)>

### GUAN_YU        = <HeroInfo.GUAN_YU: (2034, 444, 2, 16697, False)>

### ZHUGE_LIANG        = <HeroInfo.ZHUGE_LIANG: (2036, 445, 2, 16740, False)>

### ZHANG_FEI        = <HeroInfo.ZHANG_FEI: (2038, 446, 2, 16110, False)>

### SUN_CE        = <HeroInfo.SUN_CE: (2040, 447, 2, 16697, False)>

### SUN_QUAN        = <HeroInfo.SUN_QUAN: (2042, 448, 2, 16108, False)>

### ZHOU_YU        = <HeroInfo.ZHOU_YU: (2044, 449, 1969, 16456, False)>

### DONG_ZHUO        = <HeroInfo.DONG_ZHUO: (2045, 450, 1947, 16108, False)>

### YUAN_SHAO        = <HeroInfo.YUAN_SHAO: (2046, 451, 1953, 16108, False)>

### YU_JI        = <HeroInfo.YU_JI: (2047, 452, 1329, 16742, False)>

### WHITE_TIGER_YAN        = <HeroInfo.WHITE_TIGER_YAN: (2048, 453, 1950, 16217, False)>

### LIU_BIAO        = <HeroInfo.LIU_BIAO: (2049, 454, 2, 16096, False)>

### ZHANG_JUE        = <HeroInfo.ZHANG_JUE: (2050, 455, 1329, 16742, False)>

### ZHAO_YUN        = <HeroInfo.ZHAO_YUN: (2051, 456, 1373, 16108, False)>

### CAO_CAO_CAMPAIGN        = <HeroInfo.CAO_CAO_CAMPAIGN: (2052, 440, 2, 16381, False)>

### LIU_BEI_CAMPAIGN        = <HeroInfo.LIU_BEI_CAMPAIGN: (2053, 441, 2, 16381, False)>

### SUN_JIAN_CAMPAIGN        = <HeroInfo.SUN_JIAN_CAMPAIGN: (2054, 442, 2, 16381, False)>

### ALEXANDER_DISMOUNTED        = <HeroInfo.ALEXANDER_DISMOUNTED: (2397, 734, 2494, 16104, False)>

### ALEXANDER        = <HeroInfo.ALEXANDER: (2398, 733, 2502, 16724, False)>

### PHILIP        = <HeroInfo.PHILIP: (2399, 737, 2447, 16724, False)>

### PARMENION        = <HeroInfo.PARMENION: (2400, 736, 2446, 16104, False)>

### CLEITUS        = <HeroInfo.CLEITUS: (2401, 735, 2495, 16724, False)>

### HEPHAISTION        = <HeroInfo.HEPHAISTION: (2402, 739, 2447, 16104, False)>

### PERDICCAS        = <HeroInfo.PERDICCAS: (2403, 738, 2455, 16724, False)>

### NEARCHOS        = <HeroInfo.NEARCHOS: (2404, 740, 2447, 16724, False)>

### PORUS        = <HeroInfo.PORUS: (2436, 744, 2493, 16232, False)>

### THRACIAN_CHIEFTAIN        = <HeroInfo.THRACIAN_CHIEFTAIN: (2451, 707, 2452, 16695, False)>

### BUCEPHALUS        = <HeroInfo.BUCEPHALUS: (2525, 753, 2526, 16714, False)>

### LAUTARO        = <HeroInfo.LAUTARO: (2637, 570, 2, 16779, False)>

### GALVARINO        = <HeroInfo.GALVARINO: (2638, 571, 2, 16101, False)>

### GUACOLDA        = <HeroInfo.GUACOLDA: (2639, 572, 2, 16297, False)>

### PACANCHIQUE        = <HeroInfo.PACANCHIQUE: (2640, 573, 2, 16671, False)>

### ARARIBOIA        = <HeroInfo.ARARIBOIA: (2641, 574, 2, 16619, False)>

### CUNHAMBEBE        = <HeroInfo.CUNHAMBEBE: (2643, 575, 2, 16669, False)>

### HARALD        = <HeroInfo.HARALD: (2721, 921, 693, 16293, False)>

### ULF_OSPAKSSON        = <HeroInfo.ULF_OSPAKSSON: (2722, 929, 433, 16299, False)>

### HALLDOR_SNORRASON        = <HeroInfo.HALLDOR_SNORRASON: (2723, 920, 693, 16295, False)>

### TOSTIG_GODWINSON        = <HeroInfo.TOSTIG_GODWINSON: (2724, 928, 111, 16531, False)>

### FINN_ARNASON        = <HeroInfo.FINN_ARNASON: (2725, 919, 140, 16216, False)>

### KALF_ARNASON        = <HeroInfo.KALF_ARNASON: (2726, 924, 180, 16635, False)>

### EINAR_PAUNCH_SHAKER        = <HeroInfo.EINAR_PAUNCH_SHAKER: (2727, 918, 115, 16640, False)>

### DREKI        = <HeroInfo.DREKI: (2728, 595, -1, 16457, False)>


### class     StartingAge(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This is not the same as the "Age" dataset and should !!NOT!! be used in effects/conditions etc.

This enum class provides the integer values used to reference the starting ages in the game.
This is used in the player objects to set a starting age.

Examples

### class     CivilizationOld(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
Legacy enum class used to reference the civilizations in the game.

### class     Civilization(AoE2ScenarioParser.datasets.dataset_enum._DataSet):
This enum class provides the integer values used to reference the civilizations in the game.
This can be used in research tech conditions to check civ or set a player's civ in the player manager.

Examples

### DARK_AGE        = <StartingAge.DARK_AGE: 2>

### FEUDAL_AGE        = <StartingAge.FEUDAL_AGE: 3>

### CASTLE_AGE        = <StartingAge.CASTLE_AGE: 4>

### IMPERIAL_AGE        = <StartingAge.IMPERIAL_AGE: 5>

### POST_IMPERIAL_AGE        = <StartingAge.POST_IMPERIAL_AGE: 6>

### GAIA        = <CivilizationOld.GAIA: 0>

### BRITONS        = <CivilizationOld.BRITONS: 1>

### FRANKS        = <CivilizationOld.FRANKS: 2>

### GOTHS        = <CivilizationOld.GOTHS: 3>

### TEUTONS        = <CivilizationOld.TEUTONS: 4>

### JAPANESE        = <CivilizationOld.JAPANESE: 5>

### CHINESE        = <CivilizationOld.CHINESE: 6>

### BYZANTINES        = <CivilizationOld.BYZANTINES: 7>

### PERSIANS        = <CivilizationOld.PERSIANS: 8>

### SARACENS        = <CivilizationOld.SARACENS: 9>

### TURKS        = <CivilizationOld.TURKS: 10>

### VIKINGS        = <CivilizationOld.VIKINGS: 11>

### MONGOLS        = <CivilizationOld.MONGOLS: 12>

### CELTS        = <CivilizationOld.CELTS: 13>

### SPANISH        = <CivilizationOld.SPANISH: 14>

### AZTECS        = <CivilizationOld.AZTECS: 15>

### MAYANS        = <CivilizationOld.MAYANS: 16>

### HUNS        = <CivilizationOld.HUNS: 17>

### KOREANS        = <CivilizationOld.KOREANS: 18>

### ITALIANS        = <CivilizationOld.ITALIANS: 19>

### HINDUSTANIS        = <CivilizationOld.HINDUSTANIS: 20>

### INCAS        = <CivilizationOld.INCAS: 21>

### MAGYARS        = <CivilizationOld.MAGYARS: 22>

### SLAVS        = <CivilizationOld.SLAVS: 23>

### PORTUGUESE        = <CivilizationOld.PORTUGUESE: 24>

### ETHIOPIANS        = <CivilizationOld.ETHIOPIANS: 25>

### MALIANS        = <CivilizationOld.MALIANS: 26>

### BERBERS        = <CivilizationOld.BERBERS: 27>

### KHMER        = <CivilizationOld.KHMER: 28>

### MALAY        = <CivilizationOld.MALAY: 29>

### BURMESE        = <CivilizationOld.BURMESE: 30>

### VIETNAMESE        = <CivilizationOld.VIETNAMESE: 31>

### BULGARIANS        = <CivilizationOld.BULGARIANS: 32>

### TATARS        = <CivilizationOld.TATARS: 33>

### CUMANS        = <CivilizationOld.CUMANS: 34>

### LITHUANIANS        = <CivilizationOld.LITHUANIANS: 35>

### BURGUNDIANS        = <CivilizationOld.BURGUNDIANS: 36>

### SICILIANS        = <CivilizationOld.SICILIANS: 37>

### POLES        = <CivilizationOld.POLES: 38>

### BOHEMIANS        = <CivilizationOld.BOHEMIANS: 39>

### DRAVIDIANS        = <CivilizationOld.DRAVIDIANS: 40>

### BENGALIS        = <CivilizationOld.BENGALIS: 41>

### GURJARAS        = <CivilizationOld.GURJARAS: 42>

### ROMANS        = <CivilizationOld.ROMANS: 43>

### ARMENIANS        = <CivilizationOld.ARMENIANS: 44>

### GEORGIANS        = <CivilizationOld.GEORGIANS: 45>

### ACHAEMENIDS        = <CivilizationOld.ACHAEMENIDS: 46>

### ATHENIANS        = <CivilizationOld.ATHENIANS: 47>

### SPARTANS        = <CivilizationOld.SPARTANS: 48>

### SHU        = <CivilizationOld.SHU: 49>

### WU        = <CivilizationOld.WU: 50>

### WEI        = <CivilizationOld.WEI: 51>

### JURCHENS        = <CivilizationOld.JURCHENS: 52>

### KHITANS        = <CivilizationOld.KHITANS: 53>

### MACEDONIANS        = <CivilizationOld.MACEDONIANS: 54>

### THRACIANS        = <CivilizationOld.THRACIANS: 55>

### PURU        = <CivilizationOld.PURU: 56>

### MUISCA        = <CivilizationOld.MUISCA: 57>

### MAPUCHE        = <CivilizationOld.MAPUCHE: 58>

### TUPI        = <CivilizationOld.TUPI: 59>

### RANDOM        = <CivilizationOld.RANDOM: 65537>

### FULL_RANDOM        = <CivilizationOld.FULL_RANDOM: 65539>

### GAIA        = <Civilization.GAIA: 'GAIA'>

### BRITONS        = <Civilization.BRITONS: 'BRITON-CIV'>

### FRANKS        = <Civilization.FRANKS: 'FRANKISH-CIV'>

### GOTHS        = <Civilization.GOTHS: 'GOTHIC-CIV'>

### TEUTONS        = <Civilization.TEUTONS: 'TEUTONIC-CIV'>

### JAPANESE        = <Civilization.JAPANESE: 'JAPANESE-CIV'>

### CHINESE        = <Civilization.CHINESE: 'CHINESE-CIV'>

### BYZANTINES        = <Civilization.BYZANTINES: 'BYZANTINE-CIV'>

### PERSIANS        = <Civilization.PERSIANS: 'PERSIAN-CIV'>

### SARACENS        = <Civilization.SARACENS: 'SARACEN-CIV'>

### TURKS        = <Civilization.TURKS: 'TURKISH-CIV'>

### VIKINGS        = <Civilization.VIKINGS: 'VIKING-CIV'>

### MONGOLS        = <Civilization.MONGOLS: 'MONGOL-CIV'>

### CELTS        = <Civilization.CELTS: 'CELTIC-CIV'>

### SPANISH        = <Civilization.SPANISH: 'SPANISH-CIV'>

### AZTECS        = <Civilization.AZTECS: 'AZTEC-CIV'>

### MAYANS        = <Civilization.MAYANS: 'MAYAN-CIV'>

### HUNS        = <Civilization.HUNS: 'HUN-CIV'>

### KOREANS        = <Civilization.KOREANS: 'KOREAN-CIV'>

### ITALIANS        = <Civilization.ITALIANS: 'ITALIAN-CIV'>

### HINDUSTANIS        = <Civilization.HINDUSTANIS: 'INDIAN-CIV'>

### INCAS        = <Civilization.INCAS: 'INCAN-CIV'>

### MAGYARS        = <Civilization.MAGYARS: 'MAGYAR-CIV'>

### SLAVS        = <Civilization.SLAVS: 'SLAVIC-CIV'>

### PORTUGUESE        = <Civilization.PORTUGUESE: 'PORTUGUESE-CIV'>

### ETHIOPIANS        = <Civilization.ETHIOPIANS: 'ETHIOPIAN-CIV'>

### MALIANS        = <Civilization.MALIANS: 'MALIAN-CIV'>

### BERBERS        = <Civilization.BERBERS: 'BERBERS-CIV'>

### KHMER        = <Civilization.KHMER: 'KHMER-CIV'>

### MALAY        = <Civilization.MALAY: 'MALAY-CIV'>

### BURMESE        = <Civilization.BURMESE: 'BURMESE-CIV'>

### VIETNAMESE        = <Civilization.VIETNAMESE: 'VIETNAMESE-CIV'>

### BULGARIANS        = <Civilization.BULGARIANS: 'BULGARIANS-CIV'>

### TATARS        = <Civilization.TATARS: 'TATARS-CIV'>

### CUMANS        = <Civilization.CUMANS: 'CUMANS-CIV'>

### LITHUANIANS        = <Civilization.LITHUANIANS: 'LITHUANIANS-CIV'>

### BURGUNDIANS        = <Civilization.BURGUNDIANS: 'BURGUNDIANS-CIV'>

### SICILIANS        = <Civilization.SICILIANS: 'SICILIANS-CIV'>

### POLES        = <Civilization.POLES: 'POLES-CIV'>

### BOHEMIANS        = <Civilization.BOHEMIANS: 'BOHEMIANS-CIV'>

### DRAVIDIANS        = <Civilization.DRAVIDIANS: 'DRAVIDIANS-CIV'>

### BENGALIS        = <Civilization.BENGALIS: 'BENGALIS-CIV'>

### GURJARAS        = <Civilization.GURJARAS: 'GURJARAS-CIV'>

### ROMANS        = <Civilization.ROMANS: 'ROMANS-CIV'>

### ARMENIANS        = <Civilization.ARMENIANS: 'ARMENIANS-CIV'>

### GEORGIANS        = <Civilization.GEORGIANS: 'GEORGIANS-CIV'>

### ACHAEMENIDS        = <Civilization.ACHAEMENIDS: 'ACHAEMENIDS-CIV'>

### ATHENIANS        = <Civilization.ATHENIANS: 'ATHENIANS-CIV'>

### SPARTANS        = <Civilization.SPARTANS: 'SPARTANS-CIV'>

### SHU        = <Civilization.SHU: 'SHU-CIV'>

### WU        = <Civilization.WU: 'WU-CIV'>

### WEI        = <Civilization.WEI: 'WEI-CIV'>

### JURCHENS        = <Civilization.JURCHENS: 'JURCHENS-CIV'>

### KHITANS        = <Civilization.KHITANS: 'KHITANS-CIV'>

### MACEDONIANS        = <Civilization.MACEDONIANS: 'MACEDONIANS-CIV'>

### THRACIANS        = <Civilization.THRACIANS: 'THRACIANS-CIV'>

### PURU        = <Civilization.PURU: 'PURU-CIV'>

### MUISCA        = <Civilization.MUISCA: 'MUISCA-CIV'>

### MAPUCHE        = <Civilization.MAPUCHE: 'MAPUCHE-CIV'>

### TUPI        = <Civilization.TUPI: 'TUPI-CIV'>

### SAXONS        = <Civilization.SAXONS: 'SAXONS-CIV'>

### VARANGIANS        = <Civilization.VARANGIANS: 'VARANGIANS-CIV'>

### DANES        = <Civilization.DANES: 'DANES-CIV'>

### RANDOM        = <Civilization.RANDOM: 'RANDOM-CIV'>

### MIRROR_RANDOM        = <Civilization.MIRROR_RANDOM: 'MIRROR-RANDOM-CIV'>

### FULL_RANDOM        = <Civilization.FULL_RANDOM: 'FULL-RANDOM-CIV'>

### CUSTOM_RANDOM        = <Civilization.CUSTOM_RANDOM: 'CUSTOM-RANDOM-CIV'>

### def         encode(self, c):


### class     OtherInfo(AoE2ScenarioParser.datasets.support.info_dataset_base.InfoDatasetBase):
This enum class provides information about the 'Other' units in the game in the game. Information about the
following properties of a building is found in this class:

- Unit ID

- Icon ID

- Dead Unit ID

- HotKey ID

- If the unit is a gaia only unit (e.g. deer, boar, etc.)

Methods

Inherited Methods from class InfoDatasetBase

Examples

### @staticmethod
Returns:
    A list of all tree objects

### ANIMAL_SKELETON        = <OtherInfo.ANIMAL_SKELETON: (1091, -1, -1, -1, True)>

### BARRELS        = <OtherInfo.BARRELS: (1330, -1, -1, -1, True)>

### BLACK_TILE        = <OtherInfo.BLACK_TILE: (306, -1, -1, -1, True)>

### BLUE_TREE        = <OtherInfo.BLUE_TREE: (768, 32, 415, 16277, True)>

### BONFIRE        = <OtherInfo.BONFIRE: (304, -1, -1, -1, False)>

### BOX_TURTLES        = <OtherInfo.BOX_TURTLES: (1141, 282, -1, -1, True)>

### BRITISH_RELIC        = <OtherInfo.BRITISH_RELIC: (287, 26, -1, 16352, True)>

### BROKEN_CART        = <OtherInfo.BROKEN_CART: (858, -1, -1, -1, True)>

### BUDDHA_STATUE_A        = <OtherInfo.BUDDHA_STATUE_A: (1171, -1, -1, -1, True)>

### BUDDHA_STATUE_B        = <OtherInfo.BUDDHA_STATUE_B: (1172, -1, -1, -1, True)>

### BUDDHA_STATUE_C        = <OtherInfo.BUDDHA_STATUE_C: (1173, -1, -1, -1, True)>

### BUDDHA_STATUE_D        = <OtherInfo.BUDDHA_STATUE_D: (1174, -1, -1, -1, True)>

### BURNED_BUILDING_A        = <OtherInfo.BURNED_BUILDING_A: (758, -1, -1, -1, True)>

### BUSH_A        = <OtherInfo.BUSH_A: (302, 32, 415, -1, True)>

### BUSH_B        = <OtherInfo.BUSH_B: (1053, 32, 415, -1, True)>

### BUSH_C        = <OtherInfo.BUSH_C: (1054, 32, 415, -1, True)>

### BYZANTINE_RELIC        = <OtherInfo.BYZANTINE_RELIC: (288, 26, -1, 16353, True)>

### CACTUS        = <OtherInfo.CACTUS: (709, 32, -1, -1, True)>

### CHINESE_RELIC        = <OtherInfo.CHINESE_RELIC: (289, 26, -1, 16354, True)>

### CRACKS        = <OtherInfo.CRACKS: (241, -1, -1, -1, True)>

### CRATER        = <OtherInfo.CRATER: (723, -1, -1, -1, True)>

### DISMANTLED_CART        = <OtherInfo.DISMANTLED_CART: (1270, 271, -1, -1, False)>

### ES_FLAG        = <OtherInfo.ES_FLAG: (851, -1, -1, -1, False)>

### FE_FLAG        = <OtherInfo.FE_FLAG: (1285, -1, -1, -1, False)>

### FERN_PATCH        = <OtherInfo.FERN_PATCH: (1175, -1, -1, -1, True)>

### FISH_DORADO        = <OtherInfo.FISH_DORADO: (455, 275, -1, -1, True)>

### FISH_PERCH        = <OtherInfo.FISH_PERCH: (53, 276, -1, -1, True)>

### FISH_SALMON        = <OtherInfo.FISH_SALMON: (456, 277, -1, -1, True)>

### FISH_SNAPPER        = <OtherInfo.FISH_SNAPPER: (458, 278, -1, -1, True)>

### FISH_TUNA        = <OtherInfo.FISH_TUNA: (457, 279, -1, -1, True)>

### FLAG_A        = <OtherInfo.FLAG_A: (600, -1, -1, -1, False)>

### FLAG_B        = <OtherInfo.FLAG_B: (601, -1, -1, -1, False)>

### FLAG_C        = <OtherInfo.FLAG_C: (602, -1, -1, -1, False)>

### FLAG_D        = <OtherInfo.FLAG_D: (603, -1, -1, -1, False)>

### FLAG_E        = <OtherInfo.FLAG_E: (604, -1, -1, -1, False)>

### FLAG_F        = <OtherInfo.FLAG_F: (1307, -1, -1, -1, False)>

### FLAG_G        = <OtherInfo.FLAG_G: (1150, -1, -1, -1, False)>

### FLAG_H        = <OtherInfo.FLAG_H: (1151, -1, -1, -1, False)>

### FLAG_I        = <OtherInfo.FLAG_I: (1152, -1, -1, -1, False)>

### FLAG_J        = <OtherInfo.FLAG_J: (1153, -1, -1, -1, False)>

### FLAG_K        = <OtherInfo.FLAG_K: (1282, -1, -1, -1, False)>

### FLAG_L        = <OtherInfo.FLAG_L: (1283, -1, -1, -1, False)>

### FLAG_M        = <OtherInfo.FLAG_M: (1284, -1, -1, -1, False)>

### FLAG_N        = <OtherInfo.FLAG_N: (2010, -1, -1, -1, False)>

### FLAG_O        = <OtherInfo.FLAG_O: (2011, -1, -1, -1, False)>

### FLAG_P        = <OtherInfo.FLAG_P: (2012, -1, -1, -1, False)>

### FLARE        = <OtherInfo.FLARE: (274, -1, -1, -1, False)>

### FLARE_A_PERMANENT        = <OtherInfo.FLARE_A_PERMANENT: (1689, -1, -1, -1, False)>

### FLARE_B_PERMANENT        = <OtherInfo.FLARE_B_PERMANENT: (1785, -1, -1, -1, False)>

### FLOWER_BED        = <OtherInfo.FLOWER_BED: (859, -1, -1, -1, True)>

### FLOWERS_1        = <OtherInfo.FLOWERS_1: (334, -1, -1, -1, True)>

### FLOWERS_2        = <OtherInfo.FLOWERS_2: (335, -1, -1, -1, True)>

### FLOWERS_3        = <OtherInfo.FLOWERS_3: (336, -1, -1, -1, True)>

### FLOWERS_4        = <OtherInfo.FLOWERS_4: (337, -1, -1, -1, True)>

### FORAGE_BUSH        = <OtherInfo.FORAGE_BUSH: (59, 6, 415, -1, True)>

### FRANKISH_RELIC        = <OtherInfo.FRANKISH_RELIC: (290, 26, -1, 16355, True)>

### FRUIT_BUSH        = <OtherInfo.FRUIT_BUSH: (1059, 199, 415, -1, True)>

### GALLOW        = <OtherInfo.GALLOW: (1095, -1, -1, -1, True)>

### GOLD_MINE        = <OtherInfo.GOLD_MINE: (66, 14, -1, -1, True)>

### GOTHIC_RELIC        = <OtherInfo.GOTHIC_RELIC: (292, 26, -1, 16356, True)>

### GRANARY        = <OtherInfo.GRANARY: (1089, 60, 1499, -1, False)>

### GRASS_DRY        = <OtherInfo.GRASS_DRY: (1359, -1, -1, -1, True)>

### GRASS_GREEN        = <OtherInfo.GRASS_GREEN: (1358, -1, -1, -1, True)>

### GRASS_PATCH_DRY        = <OtherInfo.GRASS_PATCH_DRY: (1033, -1, -1, -1, True)>

### GRASS_PATCH_GREEN        = <OtherInfo.GRASS_PATCH_GREEN: (301, -1, -1, -1, True)>

### GRAVE        = <OtherInfo.GRAVE: (820, -1, -1, -1, True)>

### GREAT_FISH_MARLIN        = <OtherInfo.GREAT_FISH_MARLIN: (450, 281, -1, -1, True)>

### HAY_STACK        = <OtherInfo.HAY_STACK: (857, -1, -1, -1, True)>

### HEAD        = <OtherInfo.HEAD: (821, -1, -1, -1, True)>

### ICE_NAVIGABLE        = <OtherInfo.ICE_NAVIGABLE: (728, -1, -1, -1, True)>

### IMPALED_CORPSE        = <OtherInfo.IMPALED_CORPSE: (1315, -1, -1, -1, False)>

### JAPANESE_RELIC        = <OtherInfo.JAPANESE_RELIC: (294, 26, -1, 16357, True)>

### LARGE_TEMP_MAP_REVEAL        = <OtherInfo.LARGE_TEMP_MAP_REVEAL: (332, -1, -1, 16316, False)>

### MAP_REVEALER        = <OtherInfo.MAP_REVEALER: (837, -1, -1, -1, False)>

### MAP_REVEALER_MEDIUM        = <OtherInfo.MAP_REVEALER_MEDIUM: (1774, -1, -1, -1, False)>

### MAP_REVEALER_GIANT        = <OtherInfo.MAP_REVEALER_GIANT: (1775, -1, -1, -1, False)>

### MOUNTAIN_1        = <OtherInfo.MOUNTAIN_1: (310, -1, -1, -1, True)>

### MOUNTAIN_2        = <OtherInfo.MOUNTAIN_2: (311, -1, -1, -1, True)>

### MOUNTAIN_3        = <OtherInfo.MOUNTAIN_3: (744, -1, -1, -1, True)>

### MOUNTAIN_4        = <OtherInfo.MOUNTAIN_4: (745, -1, -1, -1, True)>

### MOUNTAIN_5        = <OtherInfo.MOUNTAIN_5: (1041, -1, -1, -1, True)>

### MOUNTAIN_6        = <OtherInfo.MOUNTAIN_6: (1042, -1, -1, -1, True)>

### MOUNTAIN_7        = <OtherInfo.MOUNTAIN_7: (1043, -1, -1, -1, True)>

### MOUNTAIN_8        = <OtherInfo.MOUNTAIN_8: (1044, -1, -1, -1, True)>

### NINE_BANDS        = <OtherInfo.NINE_BANDS: (720, -1, -1, -1, False)>

### NUBIAN_PYRAMID        = <OtherInfo.NUBIAN_PYRAMID: (1563, -1, -1, -1, True)>

### OLD_STONE_HEAD        = <OtherInfo.OLD_STONE_HEAD: (855, -1, -1, -1, True)>

### PAGODA_A        = <OtherInfo.PAGODA_A: (1201, -1, -1, -1, True)>

### PAGODA_B        = <OtherInfo.PAGODA_B: (1202, -1, -1, -1, True)>

### PAGODA_C        = <OtherInfo.PAGODA_C: (1203, -1, -1, -1, True)>

### TORII_GATE        = <OtherInfo.TORII_GATE: (1562, -1, -1, -1, True)>

### PATH_1        = <OtherInfo.PATH_1: (339, -1, -1, -1, True)>

### PATH_2        = <OtherInfo.PATH_2: (340, -1, -1, -1, True)>

### PATH_3        = <OtherInfo.PATH_3: (341, -1, -1, -1, True)>

### PATH_4        = <OtherInfo.PATH_4: (338, -1, -1, -1, True)>

### PERSIAN_RELIC        = <OtherInfo.PERSIAN_RELIC: (295, 26, -1, 16358, True)>

### PIECE_OF_THE_TRUE_CROSS        = <OtherInfo.PIECE_OF_THE_TRUE_CROSS: (688, -1, -1, 16570, True)>

### PLANT        = <OtherInfo.PLANT: (818, -1, -1, -1, True)>

### PLANT_BUSH_GREEN        = <OtherInfo.PLANT_BUSH_GREEN: (1360, -1, -1, -1, True)>

### PLANT_DEAD        = <OtherInfo.PLANT_DEAD: (1365, -1, -1, -1, True)>

### PLANT_FLOWERS        = <OtherInfo.PLANT_FLOWERS: (1366, -1, -1, -1, True)>

### PLANT_JUNGLE        = <OtherInfo.PLANT_JUNGLE: (1351, -1, -1, -1, True)>

### PLANT_RAINFOREST        = <OtherInfo.PLANT_RAINFOREST: (1354, -1, -1, -1, True)>

### PLANT_SHRUB_GREEN        = <OtherInfo.PLANT_SHRUB_GREEN: (1362, -1, -1, -1, True)>

### PLANT_UNDERBRUSH        = <OtherInfo.PLANT_UNDERBRUSH: (1353, -1, -1, -1, True)>

### PLANT_UNDERBRUSH_TROPICAL        = <OtherInfo.PLANT_UNDERBRUSH_TROPICAL: (1352, -1, -1, -1, True)>

### PLANT_WEEDS        = <OtherInfo.PLANT_WEEDS: (1364, -1, -1, -1, True)>

### RELIC        = <OtherInfo.RELIC: (285, 26, -1, 16350, True)>

### ROCK_1        = <OtherInfo.ROCK_1: (623, -1, -1, -1, True)>

### ROCK_2        = <OtherInfo.ROCK_2: (1323, -1, -1, -1, True)>

### ROCK_BEACH        = <OtherInfo.ROCK_BEACH: (1148, -1, -1, -1, True)>

### ROCK_FORMATION_1        = <OtherInfo.ROCK_FORMATION_1: (1048, -1, -1, -1, True)>

### ROCK_FORMATION_2        = <OtherInfo.ROCK_FORMATION_2: (1049, -1, -1, -1, True)>

### ROCK_FORMATION_3        = <OtherInfo.ROCK_FORMATION_3: (1050, -1, -1, -1, True)>

### ROCK_JUNGLE        = <OtherInfo.ROCK_JUNGLE: (1149, -1, -1, -1, True)>

### ROMAN_RUINS        = <OtherInfo.ROMAN_RUINS: (856, -1, -1, -1, True)>

### RUBBLE_1_X_1        = <OtherInfo.RUBBLE_1_X_1: (863, -1, -1, -1, False)>

### RUBBLE_2_X_2        = <OtherInfo.RUBBLE_2_X_2: (864, -1, -1, -1, False)>

### RUBBLE_3_X_3        = <OtherInfo.RUBBLE_3_X_3: (865, -1, -1, -1, False)>

### RUBBLE_4_X_4        = <OtherInfo.RUBBLE_4_X_4: (1497, -1, -1, -1, False)>

### RUBBLE_8_X_8        = <OtherInfo.RUBBLE_8_X_8: (1498, -1, -1, -1, False)>

### RUGS        = <OtherInfo.RUGS: (711, -1, -1, -1, True)>

### SARACEN_RELIC        = <OtherInfo.SARACEN_RELIC: (296, 26, -1, 16359, True)>

### SEA_ROCKS_1        = <OtherInfo.SEA_ROCKS_1: (389, -1, -1, -1, True)>

### SEA_ROCKS_2        = <OtherInfo.SEA_ROCKS_2: (396, -1, -1, -1, True)>

### SHIPWRECK_A        = <OtherInfo.SHIPWRECK_A: (721, -1, -1, -1, False)>

### SHIPWRECK_B        = <OtherInfo.SHIPWRECK_B: (722, -1, -1, -1, False)>

### SHORE_FISH        = <OtherInfo.SHORE_FISH: (69, 280, -1, -1, True)>

### SIGN        = <OtherInfo.SIGN: (819, 189, -1, -1, True)>

### SKELETON        = <OtherInfo.SKELETON: (710, -1, -1, -1, True)>

### SMALL_TEMP_MAP_REVEAL        = <OtherInfo.SMALL_TEMP_MAP_REVEAL: (112, -1, -1, 16316, False)>

### SMOKE        = <OtherInfo.SMOKE: (1308, -1, -1, -1, False)>

### SNOW_MOUNTAIN_1        = <OtherInfo.SNOW_MOUNTAIN_1: (1045, -1, -1, -1, True)>

### SNOW_MOUNTAIN_2        = <OtherInfo.SNOW_MOUNTAIN_2: (1046, -1, -1, -1, True)>

### SNOW_MOUNTAIN_3        = <OtherInfo.SNOW_MOUNTAIN_3: (1047, -1, -1, -1, True)>

### STATUE_CIVILIZATION        = <OtherInfo.STATUE_CIVILIZATION: (1279, -1, -1, -1, False)>

### STATUE_COLUMN        = <OtherInfo.STATUE_COLUMN: (1322, -1, -1, -1, True)>

### STATUE_LEFT        = <OtherInfo.STATUE_LEFT: (1343, -1, -1, -1, True)>

### STATUE_RIGHT        = <OtherInfo.STATUE_RIGHT: (1345, -1, -1, -1, True)>

### STELAE_A        = <OtherInfo.STELAE_A: (1092, -1, -1, -1, False)>

### STELAE_B        = <OtherInfo.STELAE_B: (1093, -1, -1, -1, False)>

### STELAE_C        = <OtherInfo.STELAE_C: (1094, -1, -1, -1, False)>

### STONE_MINE        = <OtherInfo.STONE_MINE: (102, 9, -1, -1, True)>

### STUMP        = <OtherInfo.STUMP: (809, -1, -1, -1, True)>

### STUPA        = <OtherInfo.STUPA: (1191, -1, -1, -1, True)>

### TARGET_A        = <OtherInfo.TARGET_A: (1564, -1, -1, -1, False)>

### TARGET_B        = <OtherInfo.TARGET_B: (1565, -1, -1, -1, False)>

### TEMPLE_RUIN        = <OtherInfo.TEMPLE_RUIN: (1566, -1, -1, -1, True)>

### TEUTONIC_RELIC        = <OtherInfo.TEUTONIC_RELIC: (297, 26, -1, 16360, True)>

### TORCH_A        = <OtherInfo.TORCH_A: (499, -1, -1, -1, False)>

### TORCH_B        = <OtherInfo.TORCH_B: (1376, -1, -1, -1, False)>

### TREE_A        = <OtherInfo.TREE_A: (399, 32, 415, -1, True)>

### TREE_ACACIA        = <OtherInfo.TREE_ACACIA: (1063, 32, 415, -1, True)>

### TREE_B        = <OtherInfo.TREE_B: (400, 32, 415, -1, True)>

### TREE_BAMBOO_FOREST        = <OtherInfo.TREE_BAMBOO_FOREST: (348, 32, 737, -1, True)>

### TREE_BAOBAB        = <OtherInfo.TREE_BAOBAB: (1052, 32, 1634, -1, True)>

### TREE_BIRCH        = <OtherInfo.TREE_BIRCH: (1717, 32, 415, -1, True)>

### TREE_C        = <OtherInfo.TREE_C: (401, 32, 415, -1, True)>

### TREE_CYPRESS        = <OtherInfo.TREE_CYPRESS: (1347, 32, 415, -1, True)>

### TREE_D        = <OtherInfo.TREE_D: (402, 32, 415, -1, True)>

### TREE_DEAD        = <OtherInfo.TREE_DEAD: (1250, 32, 415, -1, True)>

### TREE_DRAGON        = <OtherInfo.TREE_DRAGON: (1051, 32, 415, -1, True)>

### TREE_E        = <OtherInfo.TREE_E: (403, 32, 415, -1, True)>

### TREE_F        = <OtherInfo.TREE_F: (404, 32, 415, -1, True)>

### TREE_G        = <OtherInfo.TREE_G: (405, 32, 415, -1, True)>

### TREE_H        = <OtherInfo.TREE_H: (406, 32, 415, -1, True)>

### TREE_I        = <OtherInfo.TREE_I: (407, 32, 415, -1, True)>

### TREE_ITALIAN_PINE        = <OtherInfo.TREE_ITALIAN_PINE: (1348, 32, 415, -1, True)>

### TREE_J        = <OtherInfo.TREE_J: (408, 32, 415, -1, True)>

### TREE_JUNGLE        = <OtherInfo.TREE_JUNGLE: (414, 32, 415, -1, True)>

### TREE_K        = <OtherInfo.TREE_K: (409, 32, 415, -1, True)>

### TREE_L        = <OtherInfo.TREE_L: (410, 32, 415, -1, True)>

### TREE_MANGROVE        = <OtherInfo.TREE_MANGROVE: (1144, 32, 415, -1, True)>

### TREE_OAK        = <OtherInfo.TREE_OAK: (349, 32, 415, -1, True)>

### TREE_OAK_AUTUMN        = <OtherInfo.TREE_OAK_AUTUMN: (1248, 32, 415, -1, True)>

### TREE_OAK_AUTUMN_SNOW        = <OtherInfo.TREE_OAK_AUTUMN_SNOW: (1249, 32, 415, -1, True)>

### TREE_OAK_FOREST        = <OtherInfo.TREE_OAK_FOREST: (411, 32, 415, -1, True)>

### TREE_OLIVE        = <OtherInfo.TREE_OLIVE: (1349, 32, 415, -1, True)>

### TREE_PALM_FOREST        = <OtherInfo.TREE_PALM_FOREST: (351, 32, 415, -1, True)>

### TREE_PINE_FOREST        = <OtherInfo.TREE_PINE_FOREST: (350, 32, 415, -1, True)>

### TREE_RAINFOREST        = <OtherInfo.TREE_RAINFOREST: (1146, 32, 415, -1, True)>

### TREE_REEDS        = <OtherInfo.TREE_REEDS: (1350, 32, 737, -1, True)>

### TREE_SNOW_PINE        = <OtherInfo.TREE_SNOW_PINE: (413, 32, 415, -1, True)>

### TREE_TD        = <OtherInfo.TREE_TD: (284, 32, 415, -1, True)>

### TROWULAN_GATE        = <OtherInfo.TROWULAN_GATE: (1176, -1, -1, -1, True)>

### TURKISH_RELIC        = <OtherInfo.TURKISH_RELIC: (298, 26, -1, 16351, True)>

### VASES        = <OtherInfo.VASES: (1177, -1, -1, -1, True)>

### WELL        = <OtherInfo.WELL: (1567, -1, -1, -1, True)>

### DOLPHIN        = <OtherInfo.DOLPHIN: (61, 141, -1, -1, True)>

### LOOT        = <OtherInfo.LOOT: (472, -1, -1, -1, True)>

### WATERFALL_OVERLAY        = <OtherInfo.WATERFALL_OVERLAY: (896, -1, -1, -1, True)>

### QUARRY        = <OtherInfo.QUARRY: (1319, -1, -1, -1, True)>

### LUMBER        = <OtherInfo.LUMBER: (1320, -1, -1, -1, True)>

### GOODS        = <OtherInfo.GOODS: (1321, -1, -1, -1, True)>

### FLAME1        = <OtherInfo.FLAME1: (1333, -1, -1, -1, True)>

### FLAME2        = <OtherInfo.FLAME2: (1334, -1, -1, -1, True)>

### FLAME3        = <OtherInfo.FLAME3: (1335, -1, -1, -1, True)>

### FLAME4        = <OtherInfo.FLAME4: (1336, -1, -1, -1, True)>

### WATERFALL_BACKGROUND        = <OtherInfo.WATERFALL_BACKGROUND: (1635, -1, -1, -1, True)>

### BLOCKER        = <OtherInfo.BLOCKER: (1776, -1, -1, -1, True)>

### INDIAN_STATUES        = <OtherInfo.INDIAN_STATUES: (1777, -1, -1, -1, True)>

### REKHA_DEUL_TEMPLE        = <OtherInfo.REKHA_DEUL_TEMPLE: (1778, -1, -1, -1, True)>

### INDIAN_RUINS        = <OtherInfo.INDIAN_RUINS: (1784, -1, -1, -1, True)>

### SVAN_TOWER        = <OtherInfo.SVAN_TOWER: (1807, -1, -1, -1, True)>

### CLIFF_DEFAULT_1        = <OtherInfo.CLIFF_DEFAULT_1: (264, -1, -1, 16249, True)>

### CLIFF_DEFAULT_2        = <OtherInfo.CLIFF_DEFAULT_2: (265, -1, -1, 16249, True)>

### CLIFF_DEFAULT_3        = <OtherInfo.CLIFF_DEFAULT_3: (266, -1, -1, 16249, True)>

### CLIFF_DEFAULT_4        = <OtherInfo.CLIFF_DEFAULT_4: (267, -1, -1, 16249, True)>

### CLIFF_DEFAULT_5        = <OtherInfo.CLIFF_DEFAULT_5: (268, -1, -1, 16249, True)>

### CLIFF_DEFAULT_6        = <OtherInfo.CLIFF_DEFAULT_6: (269, -1, -1, 16249, True)>

### CLIFF_DEFAULT_7        = <OtherInfo.CLIFF_DEFAULT_7: (270, -1, -1, 16249, True)>

### CLIFF_DEFAULT_8        = <OtherInfo.CLIFF_DEFAULT_8: (271, -1, -1, 16249, True)>

### CLIFF_DEFAULT_9        = <OtherInfo.CLIFF_DEFAULT_9: (272, -1, -1, 16249, True)>

### CLIFF_DESERT_1        = <OtherInfo.CLIFF_DESERT_1: (1849, -1, -1, 16249, True)>

### CLIFF_DESERT_2        = <OtherInfo.CLIFF_DESERT_2: (1850, -1, -1, 16249, True)>

### CLIFF_DESERT_3        = <OtherInfo.CLIFF_DESERT_3: (1851, -1, -1, 16249, True)>

### CLIFF_DESERT_4        = <OtherInfo.CLIFF_DESERT_4: (1852, -1, -1, 16249, True)>

### CLIFF_DESERT_5        = <OtherInfo.CLIFF_DESERT_5: (1853, -1, -1, 16249, True)>

### CLIFF_DESERT_6        = <OtherInfo.CLIFF_DESERT_6: (1854, -1, -1, 16249, True)>

### CLIFF_DESERT_7        = <OtherInfo.CLIFF_DESERT_7: (1855, -1, -1, 16249, True)>

### CLIFF_DESERT_8        = <OtherInfo.CLIFF_DESERT_8: (1856, -1, -1, 16249, True)>

### CLIFF_DESERT_9        = <OtherInfo.CLIFF_DESERT_9: (1857, -1, -1, 16249, True)>

### CLIFF_SNOW_1        = <OtherInfo.CLIFF_SNOW_1: (1858, -1, -1, 16249, True)>

### CLIFF_SNOW_2        = <OtherInfo.CLIFF_SNOW_2: (1859, -1, -1, 16249, True)>

### CLIFF_SNOW_3        = <OtherInfo.CLIFF_SNOW_3: (1860, -1, -1, 16249, True)>

### CLIFF_SNOW_4        = <OtherInfo.CLIFF_SNOW_4: (1861, -1, -1, 16249, True)>

### CLIFF_SNOW_5        = <OtherInfo.CLIFF_SNOW_5: (1862, -1, -1, 16249, True)>

### CLIFF_SNOW_6        = <OtherInfo.CLIFF_SNOW_6: (1863, -1, -1, 16249, True)>

### CLIFF_SNOW_7        = <OtherInfo.CLIFF_SNOW_7: (1864, -1, -1, 16249, True)>

### CLIFF_SNOW_8        = <OtherInfo.CLIFF_SNOW_8: (1865, -1, -1, 16249, True)>

### CLIFF_SNOW_9        = <OtherInfo.CLIFF_SNOW_9: (1866, -1, -1, 16249, True)>

### OYSTERS        = <OtherInfo.OYSTERS: (2170, 701, -1, -1, True)>

### MEDITERRANEAN_RUINS        = <OtherInfo.MEDITERRANEAN_RUINS: (2234, -1, -1, -1, True)>

### MEDITERRANEAN_COURTYARD_WALLS        = <OtherInfo.MEDITERRANEAN_COURTYARD_WALLS: (2235, -1, -1, -1, True)>

### MESOPOTAMIAN_PILLAR        = <OtherInfo.MESOPOTAMIAN_PILLAR: (2251, -1, -1, -1, True)>

### MESOPOTAMIAN_GARDEN        = <OtherInfo.MESOPOTAMIAN_GARDEN: (2252, -1, -1, -1, True)>

### STATUE_ATHENA_MARBLE        = <OtherInfo.STATUE_ATHENA_MARBLE: (2264, -1, -1, -1, True)>

### STATUE_ATHENA_PAINTED        = <OtherInfo.STATUE_ATHENA_PAINTED: (2265, -1, -1, -1, True)>

### ARCHAIC_FENCE        = <OtherInfo.ARCHAIC_FENCE: (2274, -1, -1, -1, True)>

### GARDEN_HEDGE        = <OtherInfo.GARDEN_HEDGE: (2278, -1, -1, -1, True)>

### STATUE_ARES_MARBLE        = <OtherInfo.STATUE_ARES_MARBLE: (2279, -1, -1, -1, True)>

### STATUE_ARES_PAINTED        = <OtherInfo.STATUE_ARES_PAINTED: (2280, -1, -1, -1, True)>

### SIEGE_CAMP_EQUIPMENT        = <OtherInfo.SIEGE_CAMP_EQUIPMENT: (2282, -1, -1, -1, True)>

### SIEGE_CAMP_WEAPONS        = <OtherInfo.SIEGE_CAMP_WEAPONS: (2283, -1, -1, -1, True)>

### MARKET_STALL        = <OtherInfo.MARKET_STALL: (2284, -1, -1, -1, True)>

### STAKE_BARRICADE        = <OtherInfo.STAKE_BARRICADE: (2285, -1, -1, -1, True)>

### TROPAION        = <OtherInfo.TROPAION: (2286, -1, -1, -1, True)>

### MESOPOTAMIAN_TOMB        = <OtherInfo.MESOPOTAMIAN_TOMB: (2287, -1, -1, -1, True)>

### FIRE_SHRINE        = <OtherInfo.FIRE_SHRINE: (2288, -1, -1, -1, True)>

### TREASURE_CHEST        = <OtherInfo.TREASURE_CHEST: (2289, -1, -1, -1, True)>

### GRAPEVINE        = <OtherInfo.GRAPEVINE: (2290, -1, -1, -1, True)>

### LEATHERWORKING_EQUIPMENT        = <OtherInfo.LEATHERWORKING_EQUIPMENT: (2291, -1, -1, -1, True)>

### WEAPON_RACK        = <OtherInfo.WEAPON_RACK: (2293, -1, -1, -1, True)>

### SACRED_TREE        = <OtherInfo.SACRED_TREE: (2294, -1, -1, -1, True)>

### HERO_SHRINE        = <OtherInfo.HERO_SHRINE: (2306, -1, -1, -1, True)>

### MESOPOTAMIAN_RUINS        = <OtherInfo.MESOPOTAMIAN_RUINS: (2350, -1, -1, -1, True)>

### THOLOS_SHRINE        = <OtherInfo.THOLOS_SHRINE: (2351, -1, -1, -1, True)>

### AURA_QUEST_INDICATOR_LAVENDER        = <OtherInfo.AURA_QUEST_INDICATOR_LAVENDER: (2373, -1, -1, -1, True)>

### AURA_QUEST_INDICATOR_SEASHELLS        = <OtherInfo.AURA_QUEST_INDICATOR_SEASHELLS: (2378, -1, -1, -1, True)>

### AURA_QUEST_INDICATOR_COINS        = <OtherInfo.AURA_QUEST_INDICATOR_COINS: (2379, -1, -1, -1, True)>

### AURA_QUEST_INDICATOR_GOLD_AND_SHELLS        = <OtherInfo.AURA_QUEST_INDICATOR_GOLD_AND_SHELLS: (2380, -1, -1, -1, True)>

### CIV_FLAG_ACHAEMENIDS_1        = <OtherInfo.CIV_FLAG_ACHAEMENIDS_1: (2253, -1, -1, -1, False)>

### CIV_FLAG_ACHAEMENIDS_2        = <OtherInfo.CIV_FLAG_ACHAEMENIDS_2: (2254, -1, -1, -1, False)>

### CIV_FLAG_ACHAEMENIDS_3        = <OtherInfo.CIV_FLAG_ACHAEMENIDS_3: (2255, -1, -1, -1, False)>

### CIV_FLAG_ATHENIANS_1        = <OtherInfo.CIV_FLAG_ATHENIANS_1: (2256, -1, -1, -1, False)>

### CIV_FLAG_ATHENIANS_2        = <OtherInfo.CIV_FLAG_ATHENIANS_2: (2257, -1, -1, -1, False)>

### CIV_FLAG_ATHENIANS_3        = <OtherInfo.CIV_FLAG_ATHENIANS_3: (2258, -1, -1, -1, False)>

### CIV_FLAG_SPARTANS_1        = <OtherInfo.CIV_FLAG_SPARTANS_1: (2259, -1, -1, -1, False)>

### CIV_FLAG_SPARTANS_2        = <OtherInfo.CIV_FLAG_SPARTANS_2: (2260, -1, -1, -1, False)>

### CIV_FLAG_SPARTANS_3        = <OtherInfo.CIV_FLAG_SPARTANS_3: (2261, -1, -1, -1, False)>

### ANTIQUITY_TRANSPORT_SHIPWRECK        = <OtherInfo.ANTIQUITY_TRANSPORT_SHIPWRECK: (2352, -1, -1, -1, False)>

### LEVIATHAN_SHIPWRECK        = <OtherInfo.LEVIATHAN_SHIPWRECK: (2353, -1, -1, -1, False)>

### GALLEY_SHIPWRECK        = <OtherInfo.GALLEY_SHIPWRECK: (2354, -1, -1, -1, False)>

### CATAPULT_SHIPWRECK        = <OtherInfo.CATAPULT_SHIPWRECK: (2355, -1, -1, -1, False)>

### BAMBOO_STUMP        = <OtherInfo.BAMBOO_STUMP: (1536, -1, -1, -1, True)>

### BAOBAB_STUMP        = <OtherInfo.BAOBAB_STUMP: (1537, -1, -1, -1, True)>

### LUSH_BAMBOO_STUMP        = <OtherInfo.LUSH_BAMBOO_STUMP: (1538, -1, -1, -1, True)>

### FELLED_TREE        = <OtherInfo.FELLED_TREE: (1539, 32, 415, -1, True)>

### FELLED_TREE_BAMBOO        = <OtherInfo.FELLED_TREE_BAMBOO: (1540, 32, 737, -1, True)>

### FELLED_TREE_BAOBAB        = <OtherInfo.FELLED_TREE_BAOBAB: (1541, 32, 1634, -1, True)>

### FELLED_TREE_LUSH_BAMBOO        = <OtherInfo.FELLED_TREE_LUSH_BAMBOO: (1542, 32, 1985, -1, True)>

### CHAPEL        = <OtherInfo.CHAPEL: (1836, -1, -1, -1, False)>

### CASTLE_RUINS        = <OtherInfo.CASTLE_RUINS: (1837, -1, -1, -1, True)>

### CHURCH_RUINS        = <OtherInfo.CHURCH_RUINS: (1838, -1, -1, -1, True)>

### TREE_LUSH_BAMBOO_FOREST        = <OtherInfo.TREE_LUSH_BAMBOO_FOREST: (1984, 32, 1985, -1, True)>

### PAPER_LANTERN        = <OtherInfo.PAPER_LANTERN: (1986, -1, -1, -1, False)>

### CHINESE_RUINS        = <OtherInfo.CHINESE_RUINS: (1987, -1, -1, -1, True)>

### PAIFANG_GATE_SMALL        = <OtherInfo.PAIFANG_GATE_SMALL: (1989, -1, -1, -1, True)>

### PAIFANG_GATE_LARGE        = <OtherInfo.PAIFANG_GATE_LARGE: (1990, -1, -1, -1, True)>

### FOUNTAIN        = <OtherInfo.FOUNTAIN: (1991, -1, -1, -1, True)>

### PAGODA_D        = <OtherInfo.PAGODA_D: (2005, -1, -1, -1, True)>

### PAGODA_E        = <OtherInfo.PAGODA_E: (2006, -1, -1, -1, True)>

### GARDEN_PAVILION        = <OtherInfo.GARDEN_PAVILION: (2007, -1, -1, -1, True)>

### ROCK_PILLAR        = <OtherInfo.ROCK_PILLAR: (2008, -1, -1, -1, True)>

### ROCK_LIMESTONE        = <OtherInfo.ROCK_LIMESTONE: (2009, -1, -1, -1, True)>

### FLAG_RITUAL_A        = <OtherInfo.FLAG_RITUAL_A: (2013, -1, -1, -1, False)>

### FLAG_RITUAL_B        = <OtherInfo.FLAG_RITUAL_B: (2014, -1, -1, -1, False)>

### FLAG_RITUAL_C        = <OtherInfo.FLAG_RITUAL_C: (2015, -1, -1, -1, False)>

### TREE_ASIAN_PINE        = <OtherInfo.TREE_ASIAN_PINE: (2016, 32, 415, -1, True)>

### TREE_PEACH_BLOSSOM        = <OtherInfo.TREE_PEACH_BLOSSOM: (2017, 32, 415, -1, True)>

### ASIAN_CARTS        = <OtherInfo.ASIAN_CARTS: (2018, -1, -1, -1, True)>

### WEAPON_STACKS_A        = <OtherInfo.WEAPON_STACKS_A: (2019, -1, -1, -1, True)>

### GARDEN_BRIDGE        = <OtherInfo.GARDEN_BRIDGE: (2020, -1, -1, -1, True)>

### SIEGE_PROPS        = <OtherInfo.SIEGE_PROPS: (2021, -1, -1, -1, True)>

### ASIAN_LANTERNS        = <OtherInfo.ASIAN_LANTERNS: (2022, -1, -1, -1, True)>

### BURNED_BUILDING_B        = <OtherInfo.BURNED_BUILDING_B: (2023, -1, -1, -1, True)>

### ASIAN_MARKET_STALLS        = <OtherInfo.ASIAN_MARKET_STALLS: (2024, -1, -1, -1, True)>

### TREE_WILLOW        = <OtherInfo.TREE_WILLOW: (2025, 32, 415, -1, True)>

### TREE_ASIAN_MAPLE_GREEN        = <OtherInfo.TREE_ASIAN_MAPLE_GREEN: (2027, 32, 415, -1, True)>

### TREE_ASIAN_MAPLE_AUTUMN        = <OtherInfo.TREE_ASIAN_MAPLE_AUTUMN: (2028, 32, 415, -1, True)>

### FALLEN_LEAVES_PEACH_BLOSSOM        = <OtherInfo.FALLEN_LEAVES_PEACH_BLOSSOM: (2029, -1, -1, -1, True)>

### FALLEN_LEAVES_MAPLE        = <OtherInfo.FALLEN_LEAVES_MAPLE: (2030, -1, -1, -1, True)>

### FALLEN_LEAVES_MAPLE_AUTUMN        = <OtherInfo.FALLEN_LEAVES_MAPLE_AUTUMN: (2031, -1, -1, -1, True)>

### HUABIAO_TOTEM        = <OtherInfo.HUABIAO_TOTEM: (2058, -1, -1, -1, True)>

### QUE_TOWER        = <OtherInfo.QUE_TOWER: (2059, -1, -1, -1, True)>

### PANDA_ROCK        = <OtherInfo.PANDA_ROCK: (2082, -1, -1, -1, True)>

### CAVE_ROCK_1        = <OtherInfo.CAVE_ROCK_1: (2407, -1, -1, -1, True)>

### CAVE_ROCK_2        = <OtherInfo.CAVE_ROCK_2: (2408, -1, -1, -1, True)>

### CAVE_ROCK_FORMATION_1        = <OtherInfo.CAVE_ROCK_FORMATION_1: (2409, -1, -1, -1, True)>

### CAVE_ROCK_JUNGLE        = <OtherInfo.CAVE_ROCK_JUNGLE: (2410, -1, -1, -1, True)>

### CAVE_ROCK_LIMESTONE        = <OtherInfo.CAVE_ROCK_LIMESTONE: (2411, -1, -1, -1, True)>

### BLOCKER_1X3        = <OtherInfo.BLOCKER_1X3: (2423, -1, -1, -1, True)>

### BLOCKER_3X1        = <OtherInfo.BLOCKER_3X1: (2424, -1, -1, -1, True)>

### IMPALED_CORPSE_ANTIQUITY        = <OtherInfo.IMPALED_CORPSE_ANTIQUITY: (2456, -1, -1, -1, False)>

### BEACHED_WHALE        = <OtherInfo.BEACHED_WHALE: (2457, -1, -1, -1, True)>

### STATUE_HERMES        = <OtherInfo.STATUE_HERMES: (2458, -1, -1, -1, True)>

### STATUE_ARTEMIS        = <OtherInfo.STATUE_ARTEMIS: (2488, -1, -1, -1, True)>

### WATER_POTS        = <OtherInfo.WATER_POTS: (2491, -1, -1, -1, True)>

### CIV_FLAG_MACEDONIANS        = <OtherInfo.CIV_FLAG_MACEDONIANS: (2498, -1, -1, -1, False)>

### CIV_FLAG_THRACIANS        = <OtherInfo.CIV_FLAG_THRACIANS: (2499, -1, -1, -1, False)>

### CIV_FLAG_PURU        = <OtherInfo.CIV_FLAG_PURU: (2500, -1, -1, -1, False)>

### GRAIN_STORAGE        = <OtherInfo.GRAIN_STORAGE: (2501, -1, -1, -1, True)>

### BURNED_BUILDING_ACHAEMENID        = <OtherInfo.BURNED_BUILDING_ACHAEMENID: (2504, -1, -1, -1, True)>

### BURNED_BUILDING_GREEK        = <OtherInfo.BURNED_BUILDING_GREEK: (2505, -1, -1, -1, True)>

### STATUE_BENDIS        = <OtherInfo.STATUE_BENDIS: (2506, -1, -1, -1, True)>

### STATUE_SPHINX        = <OtherInfo.STATUE_SPHINX: (2507, -1, -1, -1, True)>

### BURNED_BUILDING_THRACIAN        = <OtherInfo.BURNED_BUILDING_THRACIAN: (2508, -1, -1, -1, True)>

### BURNED_BUILDING_PURU        = <OtherInfo.BURNED_BUILDING_PURU: (2509, -1, -1, -1, True)>

### FURNACE        = <OtherInfo.FURNACE: (2510, -1, -1, -1, True)>

### WATER_TROUGH        = <OtherInfo.WATER_TROUGH: (2511, -1, -1, -1, True)>

### CIV_FLAG_BOEOTIAN        = <OtherInfo.CIV_FLAG_BOEOTIAN: (2513, -1, -1, -1, False)>

### PURU_RUINS        = <OtherInfo.PURU_RUINS: (2514, -1, -1, -1, True)>

### ROCK_3        = <OtherInfo.ROCK_3: (2515, -1, -1, -1, True)>

### CAVE_ROCK_3        = <OtherInfo.CAVE_ROCK_3: (2516, -1, -1, -1, True)>

### SKELETON_ANTIQUITY_CIVILIAN        = <OtherInfo.SKELETON_ANTIQUITY_CIVILIAN: (2517, -1, -1, -1, True)>

### SKELETON_ANTIQUITY_SOLDIER        = <OtherInfo.SKELETON_ANTIQUITY_SOLDIER: (2518, -1, -1, -1, True)>

### AMPHORAE        = <OtherInfo.AMPHORAE: (2519, -1, -1, -1, True)>

### CONSTRUCTION_CRANE        = <OtherInfo.CONSTRUCTION_CRANE: (2520, -1, -1, -1, False)>

### BENCH_WOODEN        = <OtherInfo.BENCH_WOODEN: (2523, -1, -1, -1, True)>

### BENCH_STONE        = <OtherInfo.BENCH_STONE: (2524, -1, -1, -1, True)>

### SCAFFOLDING        = <OtherInfo.SCAFFOLDING: (2527, -1, -1, -1, True)>

### FOUNTAIN_ANTIQUITY        = <OtherInfo.FOUNTAIN_ANTIQUITY: (2528, -1, -1, -1, True)>

### DECORATIVE_CYPRESS_TREE        = <OtherInfo.DECORATIVE_CYPRESS_TREE: (2529, -1, -1, -1, True)>

### THEATRE        = <OtherInfo.THEATRE: (2530, -1, -1, -1, True)>

### STATUE_ALEXANDER        = <OtherInfo.STATUE_ALEXANDER: (2531, -1, -1, -1, True)>

### STATUE_HEPHAISTION        = <OtherInfo.STATUE_HEPHAISTION: (2532, -1, -1, -1, True)>

### STATUE_GREEK_HERO        = <OtherInfo.STATUE_GREEK_HERO: (2533, -1, -1, -1, True)>

### MEDITERRANEAN_STALL        = <OtherInfo.MEDITERRANEAN_STALL: (2534, -1, -1, -1, True)>

### MESOPOTAMIAN_STALL        = <OtherInfo.MESOPOTAMIAN_STALL: (2535, -1, -1, -1, True)>

### WATER_LILY        = <OtherInfo.WATER_LILY: (2536, -1, -1, -1, True)>

### STONEHENGE        = <OtherInfo.STONEHENGE: (1979, -1, -1, -1, True)>

### TREE_OAK_GREEN        = <OtherInfo.TREE_OAK_GREEN: (2567, 32, 415, -1, True)>

### TREE_MONKEY_PUZZLE        = <OtherInfo.TREE_MONKEY_PUZZLE: (2570, 32, 415, -1, True)>

### TREE_BRAZILWOOD        = <OtherInfo.TREE_BRAZILWOOD: (2580, 32, 415, -1, True)>

### TREE_WAX_PALM        = <OtherInfo.TREE_WAX_PALM: (2583, 32, 415, -1, True)>

### HOWLER_MONKEY        = <OtherInfo.HOWLER_MONKEY: (2585, -1, -1, -1, True)>

### SMALL_WATERFALL        = <OtherInfo.SMALL_WATERFALL: (2598, -1, -1, -1, True)>

### PAPAYA_TREE        = <OtherInfo.PAPAYA_TREE: (2599, 593, -1, -1, True)>

### FLAG_Q        = <OtherInfo.FLAG_Q: (2601, -1, -1, -1, False)>

### FLAG_R        = <OtherInfo.FLAG_R: (2602, -1, -1, -1, False)>

### FLAG_S        = <OtherInfo.FLAG_S: (2603, -1, -1, -1, False)>

### FLAG_T        = <OtherInfo.FLAG_T: (2604, -1, -1, -1, False)>

### FLAG_U        = <OtherInfo.FLAG_U: (2605, -1, -1, -1, False)>

### BURNED_BUILDING_C        = <OtherInfo.BURNED_BUILDING_C: (2606, -1, -1, -1, True)>

### ANDEAN_RUINS        = <OtherInfo.ANDEAN_RUINS: (2611, -1, -1, -1, True)>

### WHALE        = <OtherInfo.WHALE: (2625, 569, -1, -1, True)>

### SCAFFOLDING_WALKABLE        = <OtherInfo.SCAFFOLDING_WALKABLE: (2644, -1, -1, -1, True)>

### PINEAPPLE_BUSH        = <OtherInfo.PINEAPPLE_BUSH: (2650, 592, 415, -1, True)>

### WEAPON_STACKS_B        = <OtherInfo.WEAPON_STACKS_B: (1943, -1, -1, -1, False)>

### ROCK_MOSSY        = <OtherInfo.ROCK_MOSSY: (1967, -1, -1, -1, True)>

### KELP_SEAWEEDS        = <OtherInfo.KELP_SEAWEEDS: (1981, -1, -1, -1, True)>

### BURNED_BUILDING_E        = <OtherInfo.BURNED_BUILDING_E: (2035, -1, -1, -1, True)>

### TORCH_C        = <OtherInfo.TORCH_C: (2576, -1, -1, -1, False)>

### FLOTSAM        = <OtherInfo.FLOTSAM: (2577, -1, -1, -1, True)>

### TREE_SPRUCE        = <OtherInfo.TREE_SPRUCE: (2731, 32, 415, -1, True)>

### TREE_SPRUCE_SNOW        = <OtherInfo.TREE_SPRUCE_SNOW: (2732, 32, 415, -1, True)>

### BUSH_D        = <OtherInfo.BUSH_D: (2733, 32, 415, -1, True)>

### ROCK_SNOW        = <OtherInfo.ROCK_SNOW: (2734, -1, -1, -1, True)>

### RUNESTONES        = <OtherInfo.RUNESTONES: (2738, -1, -1, -1, True)>

### DRIFTWOOD_GROUND        = <OtherInfo.DRIFTWOOD_GROUND: (2740, -1, -1, -1, True)>

### DRIFTWOOD_WATER        = <OtherInfo.DRIFTWOOD_WATER: (2741, -1, -1, -1, True)>

### PLANT_HEATHER        = <OtherInfo.PLANT_HEATHER: (2743, -1, -1, -1, True)>

### BURNED_BUILDING_D        = <OtherInfo.BURNED_BUILDING_D: (2744, -1, -1, -1, True)>

### SHIPWRECK_C        = <OtherInfo.SHIPWRECK_C: (2746, -1, -1, -1, True)>

### NORSE_COLUMN        = <OtherInfo.NORSE_COLUMN: (2747, -1, -1, -1, True)>

### WOODEN_ROAD        = <OtherInfo.WOODEN_ROAD: (2748, -1, -1, -1, True)>

### NORSE_BANNER        = <OtherInfo.NORSE_BANNER: (2749, -1, -1, -1, False)>


### class     PlayerId(enum.IntEnum):
This enum class provides the integer values used to reference each player in the game. Use these over specifying
player number directly to improve code readability

### class     PlayerColorId(enum.IntEnum):
This enum class provides the integer values used to reference the colors in-game.
These are used in the 'Change Object Color', etc. effects

### class     ColorId(enum.IntEnum):
This enum represents the actual colors in the dropdown menu for players.
Do not confuse with the PlayerColorId which is used to reference a player number by its color.

### class     AiType(enum.IntEnum):
This enum represents the AI personality dropdown options

### @staticmethod
Return a list of all players

Args:
    exclude_gaia: if the GAIA player should be excluded from the list or not

Returns:
    The list of playerIds

### GAIA        = <PlayerId.GAIA: 0>

### ONE        = <PlayerId.ONE: 1>

### TWO        = <PlayerId.TWO: 2>

### THREE        = <PlayerId.THREE: 3>

### FOUR        = <PlayerId.FOUR: 4>

### FIVE        = <PlayerId.FIVE: 5>

### SIX        = <PlayerId.SIX: 6>

### SEVEN        = <PlayerId.SEVEN: 7>

### EIGHT        = <PlayerId.EIGHT: 8>

### BLUE        = <PlayerColorId.BLUE: 1>

### RED        = <PlayerColorId.RED: 2>

### GREEN        = <PlayerColorId.GREEN: 3>

### YELLOW        = <PlayerColorId.YELLOW: 4>

### AQUA        = <PlayerColorId.AQUA: 5>

### PURPLE        = <PlayerColorId.PURPLE: 6>

### GRAY        = <PlayerColorId.GRAY: 7>

### ORANGE        = <PlayerColorId.ORANGE: 8>

### INVALID_NEGATIVE_1        = <ColorId.INVALID_NEGATIVE_1: -1>

### BLUE        = <ColorId.BLUE: 0>

### RED        = <ColorId.RED: 1>

### GREEN        = <ColorId.GREEN: 2>

### YELLOW        = <ColorId.YELLOW: 3>

### AQUA        = <ColorId.AQUA: 4>

### PURPLE        = <ColorId.PURPLE: 5>

### GRAY        = <ColorId.GRAY: 6>

### ORANGE        = <ColorId.ORANGE: 7>

### INVALID_8        = <ColorId.INVALID_8: 8>

### INVALID_9        = <ColorId.INVALID_9: 9>

### INVALID_10        = <ColorId.INVALID_10: 10>

### INVALID_11        = <ColorId.INVALID_11: 11>

### INVALID_12        = <ColorId.INVALID_12: 12>

### INVALID_13        = <ColorId.INVALID_13: 13>

### INVALID_14        = <ColorId.INVALID_14: 14>

### INVALID_15        = <ColorId.INVALID_15: 15>

### @staticmethod

### CUSTOM        = <AiType.CUSTOM: 0>

### STANDARD        = <AiType.STANDARD: 1>

### NONE        = <AiType.NONE: 2>

### AI_CD_VERSION        = <AiType.AI_CD_VERSION: 3>


### class     ProjectileInfo(enum.Enum):
This enum class provides information about the projectiles in the game. Information about the following properties
of a projectile is found in this class:

- Projectile ID

- The units that use the projectile

Methods

Examples

### ID: int
Returns:
The ID of the specified projectile unit

### USED_BY: tuple[int]
Returns:
A tuple of unit IDs that use the specified projectile unit

### @classmethod
Get the ProjectileInfo object from its ID

Args:
    projectile_id: The ID of the projectile to get the ProjectileInfo of

Returns:
    A ProjectileInfo object of the specified projectile ID

### @staticmethod
Get the projectile object based on unit const

Args:
    unit_const: The unit to find the projectile of
    has_chemistry: If you want the fire (chemistry) version (if it exists)
    secondary: If you want the secondary projectile version (if it exists)

Returns:
    The ProjectileInfo corresponding to the given unit and params or None if nothing was found

### ARROW        = <ProjectileInfo.ARROW: (9, ())>

### VOL        = <ProjectileInfo.VOL: (54, (71, 109, 141, 142, 484, 597, 617, 621, 2275, 2276, 2277))>

### ARROW1        = <ProjectileInfo.ARROW1: (97, ())>

### SLINGER        = <ProjectileInfo.SLINGER: (187, (185, 1075, 2320, 2463))>

### CATST        = <ProjectileInfo.CATST: (242, ())>

### CATSF        = <ProjectileInfo.CATSF: (244, ())>

### BOLTX        = <ProjectileInfo.BOLTX: (245, ())>

### BOLTF        = <ProjectileInfo.BOLTF: (246, ())>

### ARROW2        = <ProjectileInfo.ARROW2: (312, ())>

### TREBST        = <ProjectileInfo.TREBST: (313, ())>

### MANGST        = <ProjectileInfo.MANGST: (314, ())>

### ARROW3        = <ProjectileInfo.ARROW3: (315, ())>

### ARROW4        = <ProjectileInfo.ARROW4: (316, ())>

### ARROW5        = <ProjectileInfo.ARROW5: (317, ())>

### ARROW6        = <ProjectileInfo.ARROW6: (318, ())>

### ARROW7        = <ProjectileInfo.ARROW7: (319, ())>

### ARROW8        = <ProjectileInfo.ARROW8: (320, ())>

### ARROW9        = <ProjectileInfo.ARROW9: (321, ())>

### ARROW10        = <ProjectileInfo.ARROW10: (322, ())>

### CATST1        = <ProjectileInfo.CATST1: (323, ())>

### CATST2        = <ProjectileInfo.CATST2: (324, ())>

### CATST3        = <ProjectileInfo.CATST3: (325, ())>

### CATST4        = <ProjectileInfo.CATST4: (326, ())>

### CATST5        = <ProjectileInfo.CATST5: (327, ())>

### VOL_FIRE        = <ProjectileInfo.VOL_FIRE: (328, (71, 109, 141, 142, 484, 597, 617, 621, 2275, 2276, 2277))>

### ARW_FLM        = <ProjectileInfo.ARW_FLM: (360, ())>

### ARC        = <ProjectileInfo.ARC: (363, (4, 158, 571, 598, 2415, 2417, 2443))>

### CROSSBOWMAN        =              <ProjectileInfo.CROSSBOWMAN: (364, (24, 493, 866, 868, 926, 930, 1072, 1106, 1166, 1294, 1297, 1759, 1761, 2174, 2175, 2468))>

### CRS        = <ProjectileInfo.CRS: (365, (7, 2562, 2564))>

### HCS        = <ProjectileInfo.HCS: (366, (6, 583, 596, 1010, 1012, 1036, 1079, 1155, 2328, 2332, 2460, 2470))>

### SCORPION        = <ProjectileInfo.SCORPION: (367, (279,))>

### BOMBARD_CANNON        = <ProjectileInfo.BOMBARD_CANNON: (368, (36, 644, 650, 1709))>

### MANGONEL_SECONDARY        = <ProjectileInfo.MANGONEL_SECONDARY: (369, (280, 550, 588, 1923, 2138, 2139))>

### TREBUCHET        = <ProjectileInfo.TREBUCHET: (371, (42, 682, 683, 1690))>

### GAL        = <ProjectileInfo.GAL: (372, (21,))>

### WAR_GALLEY        = <ProjectileInfo.WAR_GALLEY: (373, (442, 827, 829, 1750, 2339))>

### CANNON_GALLEON        = <ProjectileInfo.CANNON_GALLEON: (374, (420, 691))>

### COM_FIRE        =              <ProjectileInfo.COM_FIRE: (375, (24, 493, 866, 868, 926, 930, 1072, 1106, 1166, 1294, 1297, 1759, 1761, 2174, 2175, 2468))>

### CRS_FIRE        = <ProjectileInfo.CRS_FIRE: (376, (7, 2562, 2564))>

### HCS_FIRE        =              <ProjectileInfo.HCS_FIRE: (377, (6, 583, 596, 1010, 1012, 1036, 1079, 1155, 2328, 2332, 2460, 2470))>

### SCORPION_FIRE        = <ProjectileInfo.SCORPION_FIRE: (378, (279,))>

### GUNPOWDER_PRIMARY        = <ProjectileInfo.GUNPOWDER_PRIMARY: (380, (5, 46, 52, 203, 425, 427, 557, 748, 771, 773, 1068))>

### BOLTXF        = <ProjectileInfo.BOLTXF: (381, ())>

### BOLTF1        = <ProjectileInfo.BOLTF1: (385, ())>

### MNG_FLM        = <ProjectileInfo.MNG_FLM: (462, ())>

### ARC_FIRE        = <ProjectileInfo.ARC_FIRE: (466, (4, 158, 571, 598, 2415, 2417, 2443))>

### MANGONEL_SECONDARY_FIRE        = <ProjectileInfo.MANGONEL_SECONDARY_FIRE: (468, (280, 550, 588, 1923, 2138, 2139))>

### TREBUCHET_FIRE        = <ProjectileInfo.TREBUCHET_FIRE: (469, (42, 682, 683, 1690))>

### GALLEY_FIRE        = <ProjectileInfo.GALLEY_FIRE: (470, (21,))>

### WAR_GALLEY_FIRE        = <ProjectileInfo.WAR_GALLEY_FIRE: (471, (442, 827, 829, 1750, 2339))>

### HAR_FIRE        =              <ProjectileInfo.HAR_FIRE: (475, (11, 39, 172, 561, 577, 731, 1007, 1009, 1034, 1231, 1233, 1259, 1260, 1261, 1269, 1275, 1276, 1769, 1771, 1772, 1952, 2042, 2046, 2485, 2700, 2701))>

### HHA_FIRE        = <ProjectileInfo.HHA_FIRE: (476, (437, 474, 698, 943, 1267, 1303, 2308, 2486))>

### HAR        =              <ProjectileInfo.HAR: (477, (11, 39, 172, 561, 577, 731, 1007, 1009, 1034, 1231, 1233, 1259, 1260, 1261, 1269, 1275, 1276, 1769, 1771, 1772, 1952, 2042, 2046, 2485, 2700, 2701))>

### HHA        = <ProjectileInfo.HHA: (478, (437, 474, 698, 943, 1267, 1303, 2308, 2486))>

### T_ARO        = <ProjectileInfo.T_ARO: (485, ())>

### WTN        = <ProjectileInfo.WTN: (503, (1800, 1802))>

### ARROW_GUARD_TOWER        = <ProjectileInfo.ARROW_GUARD_TOWER: (504, (79, 234, 235, 566, 785, 1665))>

### KEP        = <ProjectileInfo.KEP: (505, (79, 234, 235, 684, 685, 785, 1102, 1665))>

### BTW        = <ProjectileInfo.BTW: (506, (236,))>

### ACA        = <ProjectileInfo.ACA: (507, (492, 642, 686, 1182, 2324, 2474))>

### DROMON        = <ProjectileInfo.DROMON: (508, (1795,))>

### VIL        = <ProjectileInfo.VIL: (509, (122, 216))>

### CKN        = <ProjectileInfo.CKN: (510, (73, 559, 1073, 1231, 1233, 1260, 2042))>

### LONGBOWMAN        =              <ProjectileInfo.LONGBOWMAN: (511, (8, 200, 530, 763, 765, 850, 1069, 1129, 1131, 2326, 2388, 2389, 2419, 2420, 2464, 2473, 2727))>

### LBT        =              <ProjectileInfo.LBT: (512, (21, 106, 250, 442, 533, 539, 778, 885, 2117, 2118, 2119, 2141, 2142, 2143, 2172, 2728))>

### MSU        = <ProjectileInfo.MSU: (513, ())>

### MPC        = <ProjectileInfo.MPC: (514, ())>

### TAX        = <ProjectileInfo.TAX: (515, (165, 281, 424, 531, 931, 1298))>

### WTN_FIRE        = <ProjectileInfo.WTN_FIRE: (516, (1800, 1802))>

### GTW_FIRE        = <ProjectileInfo.GTW_FIRE: (517, (79, 234, 235, 566, 785, 1665))>

### KEP_FIRE        = <ProjectileInfo.KEP_FIRE: (518, (79, 234, 235, 684, 685, 785, 1102, 1665))>

### ACA_FIRE        = <ProjectileInfo.ACA_FIRE: (519, (492, 642, 686, 1182, 2324, 2474))>

### DROMON_FIRE        = <ProjectileInfo.DROMON_FIRE: (520, (1795,))>

### VIL_FIRE        = <ProjectileInfo.VIL_FIRE: (521, (122, 216))>

### CKN_FIRE        = <ProjectileInfo.CKN_FIRE: (522, (73, 559, 1073, 1231, 1233, 1260, 2042))>

### LBM_FIRE        =              <ProjectileInfo.LBM_FIRE: (523, (8, 200, 530, 763, 765, 850, 1069, 1129, 1131, 2326, 2388, 2389, 2419, 2420, 2464, 2473, 2727))>

### LBT_FIRE        =              <ProjectileInfo.LBT_FIRE: (524, (21, 106, 250, 442, 533, 539, 778, 885, 2117, 2118, 2119, 2141, 2142, 2143, 2172, 2728))>

### MPC_FIRE        = <ProjectileInfo.MPC_FIRE: (525, ())>

### MSU_FIRE        = <ProjectileInfo.MSU_FIRE: (526, ())>

### BTW_FIRE        = <ProjectileInfo.BTW_FIRE: (537, (236,))>

### SLINGER_FIRE        = <ProjectileInfo.SLINGER_FIRE: (538, (185, 1075, 2320, 2463))>

### SGY        = <ProjectileInfo.SGY: (540, (2127, 2128, 2129, 2130, 2131, 2132, 2133, 2134, 2135, 2311))>

### SGY_FIRE        = <ProjectileInfo.SGY_FIRE: (541, (2127, 2128, 2129, 2130, 2131, 2132, 2133, 2134, 2135, 2311))>

### ONAGER        = <ProjectileInfo.ONAGER: (551, ())>

### ONAGER_FIRE        = <ProjectileInfo.ONAGER_FIRE: (552, ())>

### HEAVY_SCORPION        = <ProjectileInfo.HEAVY_SCORPION: (627, (542,))>

### HEAVY_SCORPION_FIRE        = <ProjectileInfo.HEAVY_SCORPION_FIRE: (628, (542,))>

### MANGONEL_PRIMARY        = <ProjectileInfo.MANGONEL_PRIMARY: (656, (280, 550, 588, 2138, 2139))>

### GP1        = <ProjectileInfo.GP1: (657, ())>

### MANGONEL_PRIMARY_FIRE        = <ProjectileInfo.MANGONEL_PRIMARY_FIRE: (658, (280, 550, 588, 2138, 2139))>

### FIRE_SHIP        = <ProjectileInfo.FIRE_SHIP: (676, (188, 190, 529, 532, 938, 1103, 1302, 2123, 2124, 2125, 2126))>

### MLK        = <ProjectileInfo.MLK: (736, (282, 556, 929, 1296))>

### CST        = <ProjectileInfo.CST: (746, (33, 82, 445, 2418, 2600))>

### CST_FIRE        = <ProjectileInfo.CST_FIRE: (747, (33, 82, 445, 2418, 2600))>

### CGX        = <ProjectileInfo.CGX: (767, (831, 832, 844, 1631))>

### KREPOST        = <ProjectileInfo.KREPOST: (786, (1251,))>

### KREPOST_FIRE        = <ProjectileInfo.KREPOST_FIRE: (787, (1251,))>

### KNIFE        = <ProjectileInfo.KNIFE: (1055, (1013, 1015, 1066))>

### CVB        = <ProjectileInfo.CVB: (1057, (1004, 1006))>

### CVB_FIRE        = <ProjectileInfo.CVB_FIRE: (1058, (1004, 1006))>

### LBOL        = <ProjectileInfo.LBOL: (1111, ())>

### LBOL_FIRE        = <ProjectileInfo.LBOL_FIRE: (1112, ())>

### HEAVY_SCORPION_UNUSED        = <ProjectileInfo.HEAVY_SCORPION_UNUSED: (1113, ())>

### HEAVY_SCORPION_FIRE_UNUSED        = <ProjectileInfo.HEAVY_SCORPION_FIRE_UNUSED: (1114, ())>

### HUSSITE_WAGON_SECONDARY        = <ProjectileInfo.HUSSITE_WAGON_SECONDARY: (1119, (203, 1704, 1706))>

### BALLISTA_ELEPHANT        = <ProjectileInfo.BALLISTA_ELEPHANT: (1167, (1120, 1122))>

### BALLISTA_ELEPHANT_FIRE        = <ProjectileInfo.BALLISTA_ELEPHANT_FIRE: (1168, (1120, 1122))>

### ARAMBAI        = <ProjectileInfo.ARAMBAI: (1169, (1126, 1128))>

### ARAMBAI_FIRE        = <ProjectileInfo.ARAMBAI_FIRE: (1170, (1126, 1128))>

### SHCOW        = <ProjectileInfo.SHCOW: (1223, ())>

### LASER        = <ProjectileInfo.LASER: (1595, (1222, 1577))>

### HUSSITE_WAGON        = <ProjectileInfo.HUSSITE_WAGON: (1733, (1704, 1706))>

### CHAKRAM        = <ProjectileInfo.CHAKRAM: (1756, (1741,))>

### THRSD        = <ProjectileInfo.THRSD: (1779, (1750,))>

### THRSD_FIRE        = <ProjectileInfo.THRSD_FIRE: (1780, (1750,))>

### ELEAR        = <ProjectileInfo.ELEAR: (1781, (873, 875))>

### ELEAR_FIRE        = <ProjectileInfo.ELEAR_FIRE: (1782, (873, 875))>

### ORGAN_GUN        = <ProjectileInfo.ORGAN_GUN: (1789, (1001, 1003))>

### DROMON_GREEK_FIRE        = <ProjectileInfo.DROMON_GREEK_FIRE: (1798, (1795,))>

### CITADELS        = <ProjectileInfo.CITADELS: (1830, (33, 82, 445, 2418, 2600))>

### SVT        = <ProjectileInfo.SVT: (1867, (79, 234, 235, 566, 684, 685, 785, 1102, 1665))>

### SVT_FIRE        = <ProjectileInfo.SVT_FIRE: (1868, (79, 234, 235, 566, 684, 685, 785, 1102, 1665))>

### LEVIATHAN        = <ProjectileInfo.LEVIATHAN: (2226, (2140, 2442, 2448))>

### GASTRAPHETES        = <ProjectileInfo.GASTRAPHETES: (2307, ())>

### POLYCRITUS        = <ProjectileInfo.POLYCRITUS: (2342, (2319,))>

### ELITECHAKRAM        = <ProjectileInfo.ELITECHAKRAM: (1783, (1743,))>

### LCHUAN_ROCKET        = <ProjectileInfo.LCHUAN_ROCKET: (1879, (1948,))>

### ROCKET_CART        = <ProjectileInfo.ROCKET_CART: (1906, (831, 832, 844, 1904, 1907))>

### GRENADIER        = <ProjectileInfo.GRENADIER: (1913, (1911,))>

### FIRE_LANCER        = <ProjectileInfo.FIRE_LANCER: (1925, (1901, 1903))>

### MOUNTED_TREBUCHET        = <ProjectileInfo.MOUNTED_TREBUCHET: (1926, (1923,))>

### MOUNTED_TREBUCHET_FIRE        = <ProjectileInfo.MOUNTED_TREBUCHET_FIRE: (1927, (1923,))>

### CROSSBOWMAN_SECONDARY        = <ProjectileInfo.CROSSBOWMAN_SECONDARY: (1930, (4, 24, 492))>

### ZHOUYU        = <ProjectileInfo.ZHOUYU: (1931, (2044,))>

### TRACTION        = <ProjectileInfo.TRACTION: (1932, (1942, 2633))>

### TRACTION_FIRE        = <ProjectileInfo.TRACTION_FIRE: (1933, (1942, 2633))>

### TRACTION_SECONDARY        = <ProjectileInfo.TRACTION_SECONDARY: (1934, (1942, 1948))>

### TRACTION_SECONDARY_FIRE        = <ProjectileInfo.TRACTION_SECONDARY_FIRE: (1935, (1942, 1948))>

### LCHUAN_CHARGE        = <ProjectileInfo.LCHUAN_CHARGE: (1936, (1948,))>

### LCHUAN_FIRE_CHARGE        = <ProjectileInfo.LCHUAN_FIRE_CHARGE: (1937, (1948,))>

### LCHUAN        = <ProjectileInfo.LCHUAN: (1938, (1948,))>

### LCHUAN_FIRE        = <ProjectileInfo.LCHUAN_FIRE: (1939, (1948,))>

### WAR_CHARIOT_BARRAGE        = <ProjectileInfo.WAR_CHARIOT_BARRAGE: (1957, (1980,))>

### WAR_CHARIOT_FOCUS_FIRE        = <ProjectileInfo.WAR_CHARIOT_FOCUS_FIRE: (1964, (1962, 2049))>

### FIRE_ARCHER        = <ProjectileInfo.FIRE_ARCHER: (1971, (1968, 1970))>

### FIRE_ARCHER_RED_CLIFFS        = <ProjectileInfo.FIRE_ARCHER_RED_CLIFFS: (1972, (1968, 1970, 2044))>

### XIANBEI        = <ProjectileInfo.XIANBEI: (1982, (1952, 2046))>

### LUBU        = <ProjectileInfo.LUBU: (2056, (2061,))>

### GSTRIKE        = <ProjectileInfo.GSTRIKE: (2057, (2065,))>

### SUNQUAN        = <ProjectileInfo.SUNQUAN: (2062, (2063,))>

### XIANBEI_SECONDARY        = <ProjectileInfo.XIANBEI_SECONDARY: (1983, (1952,))>

### HELEPOLIS        = <ProjectileInfo.HELEPOLIS: (2445, (2444,))>

### CHURCH        = <ProjectileInfo.CHURCH: (1548, (1806,))>

### BOLAS        = <ProjectileInfo.BOLAS: (2572, (2569,))>

### ELITEBOLAS        = <ProjectileInfo.ELITEBOLAS: (2573, (2571,))>

### BOLAS_CHARGE        = <ProjectileInfo.BOLAS_CHARGE: (2574, (2569,))>

### ELITEBOLAS_CHARGE        = <ProjectileInfo.ELITEBOLAS_CHARGE: (2575, (2571,))>

### BLACKWOOD_ARCHER        = <ProjectileInfo.BLACKWOOD_ARCHER: (2608, (2579,))>

### ELITE_BLACKWOOD_ARCHER        = <ProjectileInfo.ELITE_BLACKWOOD_ARCHER: (2609, (2581, 2642))>

### FIRE_SHIP_CHARGE        = <ProjectileInfo.FIRE_SHIP_CHARGE: (2629, (529, 532, 938, 1103, 1302))>

### DOCK        = <ProjectileInfo.DOCK: (2631, (45, 47, 51, 133, 1189))>

### DOCK_FIRE        = <ProjectileInfo.DOCK_FIRE: (2632, (45, 47, 51, 133, 1189))>

### HOOK        = <ProjectileInfo.HOOK: (2636, (2626, 2627, 2628))>

### HARALD        = <ProjectileInfo.HARALD: (2623, (2721,))>

### HEARTH_TROOP        = <ProjectileInfo.HEARTH_TROOP: (2702, (2705,))>

### ELITE_HEARTH_TROOP        = <ProjectileInfo.ELITE_HEARTH_TROOP: (2707, (2706,))>

### GOTHIKON        = <ProjectileInfo.GOTHIKON: (2710, ())>

### JOMSVIKING        = <ProjectileInfo.JOMSVIKING: (2713, (2711, 2712))>

### JARL        = <ProjectileInfo.JARL: (2719, (426, 2708))>

### ELITEJARL        = <ProjectileInfo.ELITEJARL: (2720, (2709,))>


### class     ScenarioVariant(enum.IntEnum):
This enum class provides the integer values used to reference the different variants of scenarios (and the game).

### LEGACY        = <ScenarioVariant.LEGACY: 0>

### AOE2        = <ScenarioVariant.AOE2: 1>

### ROR        = <ScenarioVariant.ROR: 2>

### def         to_display_name(self) -> str:

### def         applicants(self):


### datasets/support


### class     InfoDatasetBase(enum.Enum):
This enum class is the base class for the UnitInfo, BuildingInfo, HeroInfo and OtherInfo datasets. It provides the
properties and functions common to all the mentioned classes

Methods

### ID: int
Returns:
The ID of the specified unit

### ICON_ID: int
Returns:
The Icon ID of the specified unit

### DEAD_ID: int
Returns:
The Dead Unit ID of the specified unit

### HOTKEY_ID: int
Returns:
The HotKey ID of the specified unit

### IS_GAIA_ONLY: bool
Returns:
A boolean value indicating if the specified unit is a gaia only unit (e.g. Deer)

### @classmethod
Finds and returns the unit with the given unit ID

Args:
    unit_id: the unit ID to search for

Returns:
    A unit with the given unit I

### @classmethod
Finds and returns the unit with the given icon ID

Args:
    icon_id: the icon ID to search for

Returns:
    A unit with the given icon ID

### @classmethod
Finds and returns the unit with the given dead unit ID

Args:
    dead_id: the dead unit ID to search for

Returns:
    A unit with the given dead unit ID

### @classmethod
Finds and returns the unit with the given hotkey ID. Note that there may be multiple units that
use the same hotkey ID, currently only one is returned!

Args:
    hotkey_id: the hotkey ID to search for

Returns:
    A unit with the given hotkey ID

### @classmethod
Returns:
    A list of all the gaia only units (e.g. Deer)

### @classmethod
Returns:
    A list of all the units excluding gaia only units (e.g. militia)


### datasets/


### class     TechInfo(enum.Enum):
This enum class provides information about most of the techs in the game. Information about the
following properties of a tech is found in this class:

- Tech ID

- Icon ID

Methods

Examples

### ID: int
Returns:
The ID of the specified tech

### @classmethod
Get the TechInfo object from its ID

Args:
    tech_id: The ID of the tech to get the TechInfo of

Returns:
    A TechInfo object of the specified tech ID

### ICON_ID: int
Returns:
The icon ID of the specified tech

### @classmethod
Get the TechInfo object from its icon ID

Args:
    tech_icon_id: The icon ID of the tech to get the TechInfo of

Returns:
    A TechInfo object of the tech with the specified icon ID

### @staticmethod
Get the list of all the unique techs in the game

Args:
    exclude_castle_techs: if set to True,  exclude the castle age techs
    exclude_imp_techs: if set to True,  exclude the imperial age techs
    include_chronicles: if set to True, includes the chronicles techs

Returns:
    A list of TechInfo objects which are all the unique techs in the game

### @staticmethod
Args:
    exclude_castle_techs: if set to False, excludes the castle unique unit techs from the list of techs returned
    exclude_non_castle_techs: if set to False, excludes the non castle unique unit techs from the list of techs
        returned
    include_chronicles: if set to True, includes the chronicles techs to the list of techs returned

Returns:
    A list of unique unite upgrade tech IDs

### @staticmethod
Args:
    ages: a list of age IDs (IDs are located in the Age IntEnum dataset). If specified, only techs from these
        ages are returned. If unspecified, all ages' techs are returned

Returns:
    A list of TechInfo objects which are the blacksmith upgrade techs for the given age

### @staticmethod
Args:
    ages: a list of age IDs (IDs are located in the Age IntEnum dataset). If specified, only techs from these
        ages are returned. If unspecified, all ages' techs are returned

Returns:
    A list of TechInfo objects which are the blacksmith upgrade techs for the given age

### @staticmethod
Args:
    ages: The age ID (IDs are located in the Age IntEnum dataset). If specified, only techs from these
        ages are returned. If unspecified, all ages' techs are returned

Returns:
    A list of TechInfo objects which are the monastery upgrade techs for the given age

### @staticmethod
Args:
    ages: The age ID (IDs are located in the Age IntEnum dataset). If specified, only techs from these
        ages are returned. If unspecified, all ages' techs are returned

Returns:
    A list of TechInfo objects which are the university upgrade techs for the given age

### @staticmethod
Args:
    ages: The age ID (IDs are located in the Age IntEnum dataset). If specified, only techs from these
        ages are returned. If unspecified, all ages' techs are returned
    buildings: The building ID for which the upgrades are needed. If unspecified, eco upgrades from all
        economic buildings (Mill, Mining Camp, Lumber Camp, Town Center and Market) are returned

Returns:
    A list of TechInfo objects which are the eco upgrade techs for the given age

### @staticmethod
Args:
    include_chronicles: if set to True, includes the chronicles techs to the list of techs returned
Returns:
    A list of TechInfo objects which represent all civ 'upgrades'. Can be used to detect which civ is being
    played by the player using the 'researched technology' condition.

### ANARCHY        = <TechInfo.ANARCHY: (16, 33)>

### ANDEAN_SLING        = <TechInfo.ANDEAN_SLING: (516, 33)>

### ARBALESTER        = <TechInfo.ARBALESTER: (237, 54)>

### ARCHITECTURE        = <TechInfo.ARCHITECTURE: (51, 14)>

### ARQUEBUS        = <TechInfo.ARQUEBUS: (573, 107)>

### ARROWSLITS        = <TechInfo.ARROWSLITS: (608, 119)>

### ARSON        = <TechInfo.ARSON: (602, 118)>

### ARTILLERY        = <TechInfo.ARTILLERY: (10, 107)>

### ATHEISM        = <TechInfo.ATHEISM: (21, 107)>

### ATLATL        = <TechInfo.ATLATL: (460, 33)>

### ATONEMENT        = <TechInfo.ATONEMENT: (319, 93)>

### AZTECS        = <TechInfo.AZTECS: (543, -1)>

### BAGAINS        = <TechInfo.BAGAINS: (686, 107)>

### BALLISTICS        = <TechInfo.BALLISTICS: (93, 25)>

### BANKING        = <TechInfo.BANKING: (17, 3)>

### BEARDED_AXE        = <TechInfo.BEARDED_AXE: (83, 33)>

### BERBERS        = <TechInfo.BERBERS: (583, -1)>

### BOGSVEIGAR        = <TechInfo.BOGSVEIGAR: (49, 107)>

### BLAST_FURNACE        = <TechInfo.BLAST_FURNACE: (75, 21)>

### BLOCK_PRINTING        = <TechInfo.BLOCK_PRINTING: (230, 82)>

### BLOODLINES        = <TechInfo.BLOODLINES: (435, 110)>

### BODKIN_ARROW        = <TechInfo.BODKIN_ARROW: (200, 35)>

### BOMBARD_CANNON        = <TechInfo.BOMBARD_CANNON: (188, -1)>

### BOMBARD_TOWER        = <TechInfo.BOMBARD_TOWER: (64, 47)>

### BOW_SAW        = <TechInfo.BOW_SAW: (203, 71)>

### BRACER        = <TechInfo.BRACER: (201, 37)>

### BRITONS        = <TechInfo.BRITONS: (529, -1)>

### BULGARIANS        = <TechInfo.BULGARIANS: (673, -1)>

### BURMESE        = <TechInfo.BURMESE: (652, -1)>

### BYZANTINES        = <TechInfo.BYZANTINES: (535, -1)>

### CANNON_GALLEON        = <TechInfo.CANNON_GALLEON: (37, 0)>

### CAPPED_RAM        = <TechInfo.CAPPED_RAM: (96, 27)>

### CARAVAN        = <TechInfo.CARAVAN: (48, 113)>

### CAREENING        = <TechInfo.CAREENING: (374, 98)>

### CARRACK        = <TechInfo.CARRACK: (572, 33)>

### CARTOGRAPHY        = <TechInfo.CARTOGRAPHY: (19, 4)>

### CASTLE_AGE        = <TechInfo.CASTLE_AGE: (102, 31)>

### CAVALIER        = <TechInfo.CAVALIER: (209, 78)>

### CELTS        = <TechInfo.CELTS: (541, -1)>

### CHAIN_BARDING_ARMOR        = <TechInfo.CHAIN_BARDING_ARMOR: (82, 23)>

### CHAIN_MAIL_ARMOR        = <TechInfo.CHAIN_MAIL_ARMOR: (76, 22)>

### CHAMPION        = <TechInfo.CHAMPION: (264, 44)>

### CHATRAS        = <TechInfo.CHATRAS: (628, 33)>

### CHEMISTRY        = <TechInfo.CHEMISTRY: (47, 12)>

### CHINESE        = <TechInfo.CHINESE: (534, -1)>

### CHIVALRY        = <TechInfo.CHIVALRY: (493, 107)>

### COINAGE        = <TechInfo.COINAGE: (23, 7)>

### CONSCRIPTION        = <TechInfo.CONSCRIPTION: (315, 91)>

### CORVINIAN_ARMY        = <TechInfo.CORVINIAN_ARMY: (514, 33)>

### FABRIC_SHIELDS        = <TechInfo.FABRIC_SHIELDS: (517, 107)>

### CRENELLATIONS        = <TechInfo.CRENELLATIONS: (11, 107)>

### CROP_ROTATION        = <TechInfo.CROP_ROTATION: (12, 0)>

### CROSSBOWMAN        = <TechInfo.CROSSBOWMAN: (100, 29)>

### CUMAN_MERCENARIES        = <TechInfo.CUMAN_MERCENARIES: (690, 107)>

### CUMANS        = <TechInfo.CUMANS: (675, -1)>

### DARK_AGE        = <TechInfo.DARK_AGE: (104, 26)>

### DOUBLE_CROSSBOW        = <TechInfo.DOUBLE_CROSSBOW: (623, 107)>

### DOUBLE_BIT_AXE        = <TechInfo.DOUBLE_BIT_AXE: (202, 70)>

### DRILL        = <TechInfo.DRILL: (6, 107)>

### DRUZHINA        = <TechInfo.DRUZHINA: (513, 107)>

### DRY_DOCK        = <TechInfo.DRY_DOCK: (375, 99)>

### EAGLE_WARRIOR        = <TechInfo.EAGLE_WARRIOR: (384, 75)>

### HOLCANS        = <TechInfo.HOLCANS: (4, 107)>

### ELITE_ARAMBAI        = <TechInfo.ELITE_ARAMBAI: (619, 105)>

### ELITE_BALLISTA_ELEPHANT        = <TechInfo.ELITE_BALLISTA_ELEPHANT: (615, 105)>

### ELITE_BATTLE_ELEPHANT        = <TechInfo.ELITE_BATTLE_ELEPHANT: (631, 121)>

### ELITE_BERSERK        = <TechInfo.ELITE_BERSERK: (398, 105)>

### ELITE_BOYAR        = <TechInfo.ELITE_BOYAR: (504, 105)>

### ELITE_CAMEL_ARCHER        = <TechInfo.ELITE_CAMEL_ARCHER: (565, 105)>

### ELITE_CANNON_GALLEON        = <TechInfo.ELITE_CANNON_GALLEON: (376, 100)>

### ELITE_CARAVEL        = <TechInfo.ELITE_CARAVEL: (597, 105)>

### ELITE_CATAPHRACT        = <TechInfo.ELITE_CATAPHRACT: (361, 105)>

### ELITE_COUSTILLIER        = <TechInfo.ELITE_COUSTILLIER: (751, 105)>

### ELITE_CHU_KO_NU        = <TechInfo.ELITE_CHU_KO_NU: (362, 105)>

### ELITE_CONQUISTADOR        = <TechInfo.ELITE_CONQUISTADOR: (60, 105)>

### ELITE_EAGLE_WARRIOR        = <TechInfo.ELITE_EAGLE_WARRIOR: (434, 115)>

### ELITE_ELEPHANT_ARCHER        = <TechInfo.ELITE_ELEPHANT_ARCHER: (481, 127)>

### ELITE_GBETO        = <TechInfo.ELITE_GBETO: (567, 105)>

### ELITE_GENITOUR        = <TechInfo.ELITE_GENITOUR: (599, 105)>

### ELITE_GENOESE_CROSSBOWMAN        = <TechInfo.ELITE_GENOESE_CROSSBOWMAN: (468, 105)>

### ELITE_HUSKARL        = <TechInfo.ELITE_HUSKARL: (365, 105)>

### ELITE_JAGUAR_WARRIOR        = <TechInfo.ELITE_JAGUAR_WARRIOR: (432, 105)>

### ELITE_JANISSARY        = <TechInfo.ELITE_JANISSARY: (369, 105)>

### ELITE_KAMAYUK        = <TechInfo.ELITE_KAMAYUK: (509, 105)>

### ELITE_KARAMBIT_WARRIOR        = <TechInfo.ELITE_KARAMBIT_WARRIOR: (617, 105)>

### ELITE_KESHIK        = <TechInfo.ELITE_KESHIK: (680, 105)>

### ELITE_KIPCHAK        = <TechInfo.ELITE_KIPCHAK: (682, 105)>

### CHIEFTAINS        = <TechInfo.CHIEFTAINS: (463, 33)>

### ELITE_KONNIK        = <TechInfo.ELITE_KONNIK: (678, 105)>

### ELITE_LEITIS        = <TechInfo.ELITE_LEITIS: (684, 105)>

### ELITE_LONGSHIP        = <TechInfo.ELITE_LONGSHIP: (372, 68)>

### ELITE_LONGBOWMAN        = <TechInfo.ELITE_LONGBOWMAN: (360, 105)>

### ELITE_MAGYAR_HUSZAR        = <TechInfo.ELITE_MAGYAR_HUSZAR: (472, 105)>

### ELITE_MAMELUKE        = <TechInfo.ELITE_MAMELUKE: (368, 105)>

### ELITE_MANGUDAI        = <TechInfo.ELITE_MANGUDAI: (371, 105)>

### ELITE_ORGAN_GUN        = <TechInfo.ELITE_ORGAN_GUN: (563, 105)>

### ELITE_PLUMED_ARCHER        = <TechInfo.ELITE_PLUMED_ARCHER: (27, 105)>

### ELITE_RATTAN_ARCHER        = <TechInfo.ELITE_RATTAN_ARCHER: (621, 105)>

### ELITE_SAMURAI        = <TechInfo.ELITE_SAMURAI: (366, 105)>

### ELITE_SERJEANT        = <TechInfo.ELITE_SERJEANT: (753, 105)>

### ELITE_SHOTEL_WARRIOR        = <TechInfo.ELITE_SHOTEL_WARRIOR: (569, 105)>

### ELITE_SKIRMISHER        = <TechInfo.ELITE_SKIRMISHER: (98, 28)>

### ELITE_STEPPE_LANCER        = <TechInfo.ELITE_STEPPE_LANCER: (715, 123)>

### ELITE_TARKAN        = <TechInfo.ELITE_TARKAN: (2, 105)>

### ELITE_TEUTONIC_KNIGHT        = <TechInfo.ELITE_TEUTONIC_KNIGHT: (364, 105)>

### ELITE_THROWING_AXEMAN        = <TechInfo.ELITE_THROWING_AXEMAN: (363, 105)>

### ELITE_TURTLE_SHIP        = <TechInfo.ELITE_TURTLE_SHIP: (448, 105)>

### ELITE_WAR_ELEPHANT        = <TechInfo.ELITE_WAR_ELEPHANT: (367, 105)>

### ELITE_WAR_WAGON        = <TechInfo.ELITE_WAR_WAGON: (450, 105)>

### ELITE_WOAD_RAIDER        = <TechInfo.ELITE_WOAD_RAIDER: (370, 105)>

### ENABLE_COWS        = <TechInfo.ENABLE_COWS: (557, 94)>

### ENABLE_LLAMAS        = <TechInfo.ENABLE_LLAMAS: (556, 94)>

### ENABLE_SHEEP        = <TechInfo.ENABLE_SHEEP: (555, 94)>

### ENABLE_TURKEYS        = <TechInfo.ENABLE_TURKEYS: (558, 94)>

### ETHIOPIANS        = <TechInfo.ETHIOPIANS: (581, -1)>

### FAITH        = <TechInfo.FAITH: (45, 11)>

### FARIMBA        = <TechInfo.FARIMBA: (577, 107)>

### FAST_FIRE_SHIP        = <TechInfo.FAST_FIRE_SHIP: (246, 40)>

### FERVOR        = <TechInfo.FERVOR: (252, 73)>

### FEUDAL_AGE        = <TechInfo.FEUDAL_AGE: (101, 30)>

### FLETCHING        = <TechInfo.FLETCHING: (199, 34)>

### FORCED_LEVY        = <TechInfo.FORCED_LEVY: (625, 107)>

### FORGING        = <TechInfo.FORGING: (67, 17)>

### FORTIFIED_WALL        = <TechInfo.FORTIFIED_WALL: (194, 46)>

### FRANKS        = <TechInfo.FRANKS: (530, -1)>

### FUROR_CELTICA        = <TechInfo.FUROR_CELTICA: (5, 107)>

### HEAVY_WARSHIPS        = <TechInfo.HEAVY_WARSHIPS: (35, 148)>

### GARLAND_WARS        = <TechInfo.GARLAND_WARS: (24, 107)>

### GILLNETS        = <TechInfo.GILLNETS: (65, 41)>

### GOLD_MINING        = <TechInfo.GOLD_MINING: (55, 15)>

### GOLD_SHAFT_MINING        = <TechInfo.GOLD_SHAFT_MINING: (182, 62)>

### GOTHS        = <TechInfo.GOTHS: (531, -1)>

### GREAT_WALL        = <TechInfo.GREAT_WALL: (462, 33)>

### GREEK_FIRE        = <TechInfo.GREEK_FIRE: (464, 33)>

### GUARD_TOWER        = <TechInfo.GUARD_TOWER: (140, 76)>

### GUILDS        = <TechInfo.GUILDS: (15, 58)>

### HALBERDIER        = <TechInfo.HALBERDIER: (429, 106)>

### HAND_CANNON        = <TechInfo.HAND_CANNON: (85, -1)>

### HAND_CART        = <TechInfo.HAND_CART: (249, 42)>

### HEATED_SHOT        = <TechInfo.HEATED_SHOT: (380, 104)>

### HEAVY_CAMEL_RIDER        = <TechInfo.HEAVY_CAMEL_RIDER: (236, 55)>

### HEAVY_CAVALRY_ARCHER        = <TechInfo.HEAVY_CAVALRY_ARCHER: (218, 52)>

### HEAVY_DEMOLITION_SHIP        = <TechInfo.HEAVY_DEMOLITION_SHIP: (244, 39)>

### HEAVY_PLOW        = <TechInfo.HEAVY_PLOW: (13, 1)>

### HEAVY_SCORPION        = <TechInfo.HEAVY_SCORPION: (239, 38)>

### HERBAL_MEDICINE        = <TechInfo.HERBAL_MEDICINE: (441, 114)>

### HERESY        = <TechInfo.HERESY: (439, 108)>

### HILL_FORTS        = <TechInfo.HILL_FORTS: (691, 33)>

### HOARDINGS        = <TechInfo.HOARDINGS: (379, 103)>

### HORSE_COLLAR        = <TechInfo.HORSE_COLLAR: (14, 2)>

### HOWDAH        = <TechInfo.HOWDAH: (626, 107)>

### HUNS        = <TechInfo.HUNS: (545, -1)>

### HUSBANDRY        = <TechInfo.HUSBANDRY: (39, 10)>

### HUSSAR        = <TechInfo.HUSSAR: (428, 122)>

### ILLUMINATION        = <TechInfo.ILLUMINATION: (233, 84)>

### IMPERIAL_AGE        = <TechInfo.IMPERIAL_AGE: (103, 32)>

### IMPERIAL_CAMEL_RIDER        = <TechInfo.IMPERIAL_CAMEL_RIDER: (521, 74)>

### IMPERIAL_SKIRMISHER        = <TechInfo.IMPERIAL_SKIRMISHER: (655, 120)>

### INCA        = <TechInfo.INCA: (549, -1)>

### HINDUSTANIS        = <TechInfo.HINDUSTANIS: (548, -1)>

### INQUISITION        = <TechInfo.INQUISITION: (492, 33)>

### IRON_CASTING        = <TechInfo.IRON_CASTING: (68, 18)>

### IRONCLAD        = <TechInfo.IRONCLAD: (489, 33)>

### ITALIANS        = <TechInfo.ITALIANS: (547, -1)>

### JAPANESE        = <TechInfo.JAPANESE: (533, -1)>

### KAMANDARAN        = <TechInfo.KAMANDARAN: (488, 33)>

### KASBAH        = <TechInfo.KASBAH: (578, 33)>

### KATAPARUTO        = <TechInfo.KATAPARUTO: (59, 107)>

### KEEP        = <TechInfo.KEEP: (63, 16)>

### KHMER        = <TechInfo.KHMER: (650, -1)>

### KOREANS        = <TechInfo.KOREANS: (546, -1)>

### LEATHER_ARCHER_ARMOR        = <TechInfo.LEATHER_ARCHER_ARMOR: (212, 50)>

### LIGHT_CAVALRY        = <TechInfo.LIGHT_CAVALRY: (254, 43)>

### LITHUANIANS        = <TechInfo.LITHUANIANS: (676, -1)>

### LOGISTICA        = <TechInfo.LOGISTICA: (61, 107)>

### LONG_SWORDSMAN        = <TechInfo.LONG_SWORDSMAN: (207, 48)>

### LOOM        = <TechInfo.LOOM: (22, 6)>

### MADRASAH        = <TechInfo.MADRASAH: (490, 33)>

### MAGHREBI_CAMELS        = <TechInfo.MAGHREBI_CAMELS: (579, 107)>

### MAGYARS        = <TechInfo.MAGYARS: (550, -1)>

### CITADELS        = <TechInfo.CITADELS: (7, 107)>

### MALAY        = <TechInfo.MALAY: (651, -1)>

### MALIANS        = <TechInfo.MALIANS: (582, -1)>

### MAN_AT_ARMS        = <TechInfo.MAN_AT_ARMS: (222, 85)>

### MANIPUR_CAVALRY        = <TechInfo.MANIPUR_CAVALRY: (627, 33)>

### MARAUDERS        = <TechInfo.MARAUDERS: (483, 33)>

### MASONRY        = <TechInfo.MASONRY: (50, 13)>

### MAYA        = <TechInfo.MAYA: (544, -1)>

### MONGOLS        = <TechInfo.MONGOLS: (540, -1)>

### MURDER_HOLES        = <TechInfo.MURDER_HOLES: (322, 61)>

### NOMADS        = <TechInfo.NOMADS: (487, 33)>

### HULCHE_JAVELINEERS        = <TechInfo.HULCHE_JAVELINEERS: (485, 33)>

### ONAGER        = <TechInfo.ONAGER: (257, 57)>

### ORTHODOXY        = <TechInfo.ORTHODOXY: (512, 33)>

### PADDED_ARCHER_ARMOR        = <TechInfo.PADDED_ARCHER_ARMOR: (211, 49)>

### PALADIN        = <TechInfo.PALADIN: (265, 45)>

### EUPSEONG        = <TechInfo.EUPSEONG: (486, 33)>

### PAPER_MONEY        = <TechInfo.PAPER_MONEY: (629, 107)>

### PARTHIAN_TACTICS        = <TechInfo.PARTHIAN_TACTICS: (436, 111)>

### PAVISE        = <TechInfo.PAVISE: (494, 33)>

### PERFUSION        = <TechInfo.PERFUSION: (457, 107)>

### PERSIANS        = <TechInfo.PERSIANS: (536, -1)>

### PIKEMAN        = <TechInfo.PIKEMAN: (197, 36)>

### PLATE_BARDING_ARMOR        = <TechInfo.PLATE_BARDING_ARMOR: (80, 65)>

### PLATE_MAIL_ARMOR        = <TechInfo.PLATE_MAIL_ARMOR: (77, 64)>

### PORTUGUESE        = <TechInfo.PORTUGUESE: (580, -1)>

### RECURVE_BOW        = <TechInfo.RECURVE_BOW: (515, 107)>

### REDEMPTION        = <TechInfo.REDEMPTION: (316, 92)>

### REVETMENTS        = <TechInfo.REVETMENTS: (525, -1)>

### RING_ARCHER_ARMOR        = <TechInfo.RING_ARCHER_ARMOR: (219, 51)>

### ROCKETRY        = <TechInfo.ROCKETRY: (52, 107)>

### ROYAL_HEIRS        = <TechInfo.ROYAL_HEIRS: (574, 33)>

### SANCTITY        = <TechInfo.SANCTITY: (231, 83)>

### SAPPERS        = <TechInfo.SAPPERS: (321, 5)>

### SARACENS        = <TechInfo.SARACENS: (537, -1)>

### SCALE_BARDING_ARMOR        = <TechInfo.SCALE_BARDING_ARMOR: (81, 66)>

### SCALE_MAIL_ARMOR        = <TechInfo.SCALE_MAIL_ARMOR: (74, 63)>

### SCORPION        = <TechInfo.SCORPION: (94, -1)>

### SET_MAXIMUM_POPULATION_NO_HOUSES        = <TechInfo.SET_MAXIMUM_POPULATION_NO_HOUSES: (658, -1)>

### SHATAGNI        = <TechInfo.SHATAGNI: (507, 107)>

### SHINKICHON        = <TechInfo.SHINKICHON: (445, 107)>

### SHIPWRIGHT        = <TechInfo.SHIPWRIGHT: (373, 97)>

### SIEGE_ENGINEERS        = <TechInfo.SIEGE_ENGINEERS: (377, 101)>

### SIEGE_ONAGER        = <TechInfo.SIEGE_ONAGER: (320, 96)>

### SIEGE_RAM        = <TechInfo.SIEGE_RAM: (255, 86)>

### SILK_ARMOR        = <TechInfo.SILK_ARMOR: (687, 33)>

### SILK_ROAD        = <TechInfo.SILK_ROAD: (499, 33)>

### SIPAHI        = <TechInfo.SIPAHI: (491, 33)>

### SLAVS        = <TechInfo.SLAVS: (551, -1)>

### SPANISH        = <TechInfo.SPANISH: (542, -1)>

### SPIES_AND_TREASON        = <TechInfo.SPIES_AND_TREASON: (408, 19)>

### SQUIRES        = <TechInfo.SQUIRES: (215, 80)>

### STEPPE_HUSBANDRY        = <TechInfo.STEPPE_HUSBANDRY: (689, 33)>

### STIRRUPS        = <TechInfo.STIRRUPS: (685, 33)>

### STONE_MINING        = <TechInfo.STONE_MINING: (278, 87)>

### STONE_SHAFT_MINING        = <TechInfo.STONE_SHAFT_MINING: (279, 88)>

### STRONGHOLD        = <TechInfo.STRONGHOLD: (482, 33)>

### GRAND_TRUNK_ROAD        = <TechInfo.GRAND_TRUNK_ROAD: (506, 33)>

### SUPPLIES        = <TechInfo.SUPPLIES: (716, 124)>

### SUPREMACY        = <TechInfo.SUPREMACY: (440, 107)>

### TATARS        = <TechInfo.TATARS: (674, -1)>

### TEUTONS        = <TechInfo.TEUTONS: (532, -1)>

### THALASSOCRACY        = <TechInfo.THALASSOCRACY: (624, 33)>

### THEOCRACY        = <TechInfo.THEOCRACY: (438, 109)>

### THUMB_RING        = <TechInfo.THUMB_RING: (437, 112)>

### TIGUI        = <TechInfo.TIGUI: (576, 33)>

### TIMURID_SIEGECRAFT        = <TechInfo.TIMURID_SIEGECRAFT: (688, 107)>

### TORSION_ENGINES        = <TechInfo.TORSION_ENGINES: (575, 107)>

### TOWER_SHIELDS        = <TechInfo.TOWER_SHIELDS: (692, 107)>

### TOWN_CENTER_SPAWN        = <TechInfo.TOWN_CENTER_SPAWN: (639, -1)>

### TOWN_PATROL        = <TechInfo.TOWN_PATROL: (280, 89)>

### TOWN_WATCH        = <TechInfo.TOWN_WATCH: (8, 69)>

### TRACKING        = <TechInfo.TRACKING: (90, 67)>

### TREADMILL_CRANE        = <TechInfo.TREADMILL_CRANE: (54, 60)>

### TURKS        = <TechInfo.TURKS: (538, -1)>

### TUSK_SWORDS        = <TechInfo.TUSK_SWORDS: (622, 33)>

### TWO_HANDED_SWORDSMAN        = <TechInfo.TWO_HANDED_SWORDSMAN: (217, 53)>

### TWO_MAN_SAW        = <TechInfo.TWO_MAN_SAW: (221, 81)>

### VIETNAMESE        = <TechInfo.VIETNAMESE: (653, -1)>

### VIETNAMESE_VISION        = <TechInfo.VIETNAMESE_VISION: (665, -1)>

### VIKINGS        = <TechInfo.VIKINGS: (539, -1)>

### MEDIUM_WARSHIPS        = <TechInfo.MEDIUM_WARSHIPS: (34, 147)>

### WARWOLF        = <TechInfo.WARWOLF: (461, 107)>

### WHEELBARROW        = <TechInfo.WHEELBARROW: (213, 79)>

### YASAMA        = <TechInfo.YASAMA: (484, 33)>

### YEOMEN        = <TechInfo.YEOMEN: (3, 33)>

### ZEALOTRY        = <TechInfo.ZEALOTRY: (9, 107)>

### SICILIANS        = <TechInfo.SICILIANS: (749, -1)>

### BURGUNDIANS        = <TechInfo.BURGUNDIANS: (748, -1)>

### BURGUNDIAN_VINEYARDS        = <TechInfo.BURGUNDIAN_VINEYARDS: (754, 33)>

### FLEMISH_REVOLUTION        = <TechInfo.FLEMISH_REVOLUTION: (755, 107)>

### FIRST_CRUSADE        = <TechInfo.FIRST_CRUSADE: (756, 33)>

### HAUBERK        = <TechInfo.HAUBERK: (757, 107)>

### POLES        = <TechInfo.POLES: (776, -1)>

### SZLACHTA_PRIVILEGES        = <TechInfo.SZLACHTA_PRIVILEGES: (782, 33)>

### LECHITIC_LEGACY        = <TechInfo.LECHITIC_LEGACY: (783, 107)>

### FOLWARK        = <TechInfo.FOLWARK: (793, -1)>

### FOLWARK_FEUDAL        = <TechInfo.FOLWARK_FEUDAL: (794, -1)>

### FOLWARK_CASTLE        = <TechInfo.FOLWARK_CASTLE: (795, -1)>

### FOLWARK_IMPERIAL        = <TechInfo.FOLWARK_IMPERIAL: (796, -1)>

### FLEMISH_MILITIA_IMPERIAL        = <TechInfo.FLEMISH_MILITIA_IMPERIAL: (797, -1)>

### BOHEMIANS        = <TechInfo.BOHEMIANS: (777, -1)>

### WAGENBURG_TACTICS        = <TechInfo.WAGENBURG_TACTICS: (784, 33)>

### HUSSITE_REFORMS        = <TechInfo.HUSSITE_REFORMS: (785, 107)>

### WINGED_HUSSAR        = <TechInfo.WINGED_HUSSAR: (786, 125)>

### HOUFNICE        = <TechInfo.HOUFNICE: (787, 126)>

### ELITE_HUSSITE_WAGON        = <TechInfo.ELITE_HUSSITE_WAGON: (781, 105)>

### ELITE_OBUCH        = <TechInfo.ELITE_OBUCH: (779, 105)>

### SET_MAX_POP        = <TechInfo.SET_MAXIMUM_POPULATION_NO_HOUSES: (658, -1)>

### ENABLE_MONUMENT_RES_TRICKLE        = <TechInfo.ENABLE_MONUMENT_RES_TRICKLE: (729, -1)>

### RESOURCES_LAST_15_PERCENT_LONGER        = <TechInfo.RESOURCES_LAST_15_PERCENT_LONGER: (737, -1)>

### RESOURCES_LAST_30_PERCENT_LONGER        = <TechInfo.RESOURCES_LAST_30_PERCENT_LONGER: (738, -1)>

### RESOURCES_LAST_40_PERCENT_LONGER        = <TechInfo.RESOURCES_LAST_40_PERCENT_LONGER: (739, -1)>

### RESOURCES_LAST_50_PERCENT_LONGER        = <TechInfo.RESOURCES_LAST_50_PERCENT_LONGER: (740, -1)>

### RESOURCES_LAST_75_PERCENT_LONGER        = <TechInfo.RESOURCES_LAST_75_PERCENT_LONGER: (741, -1)>

### RESOURCES_LAST_100_PERCENT_LONGER        = <TechInfo.RESOURCES_LAST_100_PERCENT_LONGER: (742, -1)>

### RESOURCES_LAST_125_PERCENT_LONGER        = <TechInfo.RESOURCES_LAST_125_PERCENT_LONGER: (743, -1)>

### RESOURCES_LAST_150_PERCENT_LONGER        = <TechInfo.RESOURCES_LAST_150_PERCENT_LONGER: (744, -1)>

### RESOURCES_LAST_175_PERCENT_LONGER        = <TechInfo.RESOURCES_LAST_175_PERCENT_LONGER: (745, -1)>

### RESOURCES_LAST_200_PERCENT_LONGER        = <TechInfo.RESOURCES_LAST_200_PERCENT_LONGER: (746, -1)>

### RESOURCES_LAST_300_PERCENT_LONGER        = <TechInfo.RESOURCES_LAST_300_PERCENT_LONGER: (747, -1)>

### AUTO_UPGRADE_SCOUT_FEUDAL_AGE        = <TechInfo.AUTO_UPGRADE_SCOUT_FEUDAL_AGE: (20, 0)>

### BIMARISTAN        = <TechInfo.BIMARISTAN: (28, 33)>

### WALLS_HP_CASTLE_AGE        = <TechInfo.WALLS_HP_CASTLE_AGE: (71, -1)>

### PALISADE_WALLS_HP_FEUDAL_AGE        = <TechInfo.PALISADE_WALLS_HP_FEUDAL_AGE: (72, -1)>

### COUNTERWEIGHTS        = <TechInfo.COUNTERWEIGHTS: (454, 107)>

### DETINETS        = <TechInfo.DETINETS: (455, 33)>

### ARROWSLITS_GUARD_TOWER        = <TechInfo.ARROWSLITS_GUARD_TOWER: (610, -1)>

### ARROWSLITS_KEEP        = <TechInfo.ARROWSLITS_KEEP: (611, -1)>

### XOLOTL_POST_IMPERIAL_UPGRADE        = <TechInfo.XOLOTL_POST_IMPERIAL_UPGRADE: (636, -1)>

### IMPERIAL_NOMADS        = <TechInfo.IMPERIAL_NOMADS: (641, -1)>

### THALASSOCRACY_AND_FLETCHING        = <TechInfo.THALASSOCRACY_AND_FLETCHING: (669, -1)>

### THALASSOCRACY_AND_BODKIN        = <TechInfo.THALASSOCRACY_AND_BODKIN: (670, -1)>

### THALASSOCRACY_AND_BRACER        = <TechInfo.THALASSOCRACY_AND_BRACER: (671, -1)>

### RENAME_UNITS        = <TechInfo.RENAME_UNITS: (713, -1)>

### FTT_DISABLE_PAPHOS_REGIONALS        = <TechInfo.FTT_DISABLE_PAPHOS_REGIONALS: (717, 0)>

### FTT_MOVE_TARKANS        = <TechInfo.FTT_MOVE_TARKANS: (718, 0)>

### FTT_MOVE_HUSKARLS        = <TechInfo.FTT_MOVE_HUSKARLS: (719, 0)>

### FTT_MOVE_SLINGERS        = <TechInfo.FTT_MOVE_SLINGERS: (720, 0)>

### CHANGE_TC_CONSTR_TIME1        = <TechInfo.CHANGE_TC_CONSTR_TIME1: (723, 0)>

### CHANGE_TC_CONSTR_TIME2        = <TechInfo.CHANGE_TC_CONSTR_TIME2: (724, 0)>

### THALASSOCRACY_AND_CHEMISTRY        = <TechInfo.THALASSOCRACY_AND_CHEMISTRY: (734, -1)>

### THALASSOCRACY_AND_MURDER_HOLES        = <TechInfo.THALASSOCRACY_AND_MURDER_HOLES: (735, -1)>

### THALASSOCRACY_AND_HEATED_SHOT        = <TechInfo.THALASSOCRACY_AND_HEATED_SHOT: (736, -1)>

### FEUDAL_ECO_TECH_REQUIREMENT        = <TechInfo.FEUDAL_ECO_TECH_REQUIREMENT: (758, -1)>

### CASTLE_ECO_TECH_REQUIREMENT        = <TechInfo.CASTLE_ECO_TECH_REQUIREMENT: (759, -1)>

### IMPERIAL_ECO_TECH_REQUIREMENT        = <TechInfo.IMPERIAL_ECO_TECH_REQUIREMENT: (760, -1)>

### HEAVY_PLOW_REQUIREMENT        = <TechInfo.HEAVY_PLOW_REQUIREMENT: (761, -1)>

### BOW_SAW_REQUIREMENT        = <TechInfo.BOW_SAW_REQUIREMENT: (762, -1)>

### HAND_CART_REQUIREMENT        = <TechInfo.HAND_CART_REQUIREMENT: (763, -1)>

### GOLD_SHAFT_MINING_REQUIREMENT        = <TechInfo.GOLD_SHAFT_MINING_REQUIREMENT: (764, -1)>

### STONE_SHAFT_MINING_REQUIREMENT        = <TechInfo.STONE_SHAFT_MINING_REQUIREMENT: (765, -1)>

### CROP_ROTATION_REQUIREMENT        = <TechInfo.CROP_ROTATION_REQUIREMENT: (766, -1)>

### TWO_MAN_SAW_REQUIREMENT        = <TechInfo.TWO_MAN_SAW_REQUIREMENT: (767, -1)>

### CAVALIER_REQUIREMENT        = <TechInfo.CAVALIER_REQUIREMENT: (768, -1)>

### WINGED_HUSSAR_LITHUANIANS        = <TechInfo.WINGED_HUSSAR_LITHUANIANS: (788, -1)>

### WINGED_HUSSAR_POLES        = <TechInfo.WINGED_HUSSAR_POLES: (789, -1)>

### DRAVIDIANS        = <TechInfo.DRAVIDIANS: (822, -1)>

### BENGALIS        = <TechInfo.BENGALIS: (823, -1)>

### GURJARAS        = <TechInfo.GURJARAS: (824, -1)>

### ELITE_URUMI_SWORDSMAN        = <TechInfo.ELITE_URUMI_SWORDSMAN: (826, 105)>

### ELITE_RATHA        = <TechInfo.ELITE_RATHA: (828, 105)>

### ELITE_CHAKRAM_THROWER        = <TechInfo.ELITE_CHAKRAM_THROWER: (830, 105)>

### MEDICAL_CORPS        = <TechInfo.MEDICAL_CORPS: (831, 33)>

### WOOTZ_STEEL        = <TechInfo.WOOTZ_STEEL: (832, 107)>

### PAIKS        = <TechInfo.PAIKS: (833, 33)>

### MAHAYANA        = <TechInfo.MAHAYANA: (834, 107)>

### KSHATRIYAS        = <TechInfo.KSHATRIYAS: (835, 33)>

### FRONTIER_GUARDS        = <TechInfo.FRONTIER_GUARDS: (836, 107)>

### SIEGE_ELEPHANT        = <TechInfo.SIEGE_ELEPHANT: (838, 128)>

### ELITE_GHULAM        = <TechInfo.ELITE_GHULAM: (840, 105)>

### ELITE_SHRIVAMSHA_RIDER        = <TechInfo.ELITE_SHRIVAMSHA_RIDER: (843, 105)>

### UPGRADE_CAMEL_SCOUTS_TO_RIDERS        = <TechInfo.UPGRADE_CAMEL_SCOUTS_TO_RIDERS: (860, -1)>

### KSHATRIYAS_AND_SUPPLIES        = <TechInfo.KSHATRIYAS_AND_SUPPLIES: (861, -1)>

### FTT_MOVE_TARKANS_2        = <TechInfo.FTT_MOVE_TARKANS_2: (862, 0)>

### FTT_MOVE_ELEPHANT_ARCHERS        = <TechInfo.FTT_MOVE_ELEPHANT_ARCHERS: (863, 0)>

### FTT_MOVE_ARMORED_ELEPHANTS        = <TechInfo.FTT_MOVE_ARMORED_ELEPHANTS: (864, 0)>

### FTT_MOVE_SHRIVAMSHA_RIDERS        = <TechInfo.FTT_MOVE_SHRIVAMSHA_RIDERS: (865, 0)>

### FTT_MOVE_SHRIVAMSHA_RIDERS_2        = <TechInfo.FTT_MOVE_SHRIVAMSHA_RIDERS_2: (866, 0)>

### PAPER_MONEY_AND_DOUBLE_BIT_AXE        = <TechInfo.PAPER_MONEY_AND_DOUBLE_BIT_AXE: (867, -1)>

### PAPER_MONEY_AND_BOW_SAW        = <TechInfo.PAPER_MONEY_AND_BOW_SAW: (868, -1)>

### PAPER_MONEY_AND_TWO_MAN_SAW        = <TechInfo.PAPER_MONEY_AND_TWO_MAN_SAW: (869, -1)>

### GAMBESONS        = <TechInfo.GAMBESONS: (875, 116)>

### ROMANS        = <TechInfo.ROMANS: (880, -1)>

### ELITE_CENTURION        = <TechInfo.ELITE_CENTURION: (882, 105)>

### BALLISTAS        = <TechInfo.BALLISTAS: (883, 33)>

### COMITATENSES        = <TechInfo.COMITATENSES: (884, 107)>

### LEGIONARY        = <TechInfo.LEGIONARY: (885, 129)>

### DEVOTION        = <TechInfo.DEVOTION: (46, 131)>

### ARMENIANS        = <TechInfo.ARMENIANS: (915, -1)>

### GEORGIANS        = <TechInfo.GEORGIANS: (916, -1)>

### ELITE_COMPOSITE_BOWMAN        = <TechInfo.ELITE_COMPOSITE_BOWMAN: (918, 105)>

### ELITE_MONASPA        = <TechInfo.ELITE_MONASPA: (920, 105)>

### FERETERS        = <TechInfo.FERETERS: (921, 107)>

### CILICIAN_FLEET        = <TechInfo.CILICIAN_FLEET: (922, 33)>

### SVAN_TOWERS        = <TechInfo.SVAN_TOWERS: (923, 33)>

### AZNAURI_CAVALRY        = <TechInfo.AZNAURI_CAVALRY: (924, 107)>

### FORTIFIED_CHURCH_GEORGIANS        = <TechInfo.FORTIFIED_CHURCH_GEORGIANS: (930, -1)>

### FORTIFIED_CHURCH_ARMENIANS        = <TechInfo.FORTIFIED_CHURCH_ARMENIANS: (941, -1)>

### FORTIFIED_CHURCH_AND_SVAN_TOWERS        = <TechInfo.FORTIFIED_CHURCH_AND_SVAN_TOWERS: (931, -1)>

### MULE_CART_MAKE_AVAILABLE        = <TechInfo.MULE_CART_MAKE_AVAILABLE: (932, -1)>

### SVAN_TOWERS_AND_CHEMISTRY        = <TechInfo.SVAN_TOWERS_AND_CHEMISTRY: (936, -1)>

### FORTIFIED_CHURCH_AND_FLETCHING        = <TechInfo.FORTIFIED_CHURCH_AND_FLETCHING: (943, -1)>

### FORTIFIED_CHURCH_AND_BODKIN        = <TechInfo.FORTIFIED_CHURCH_AND_BODKIN: (944, -1)>

### FORTIFIED_CHURCH_AND_BRACER        = <TechInfo.FORTIFIED_CHURCH_AND_BRACER: (945, -1)>

### FORTIFIED_CHURCH_AND_CHEMISTRY        = <TechInfo.FORTIFIED_CHURCH_AND_CHEMISTRY: (946, -1)>

### FORTIFIED_CHURCH_AND_MURDER_HOLES        = <TechInfo.FORTIFIED_CHURCH_AND_MURDER_HOLES: (947, -1)>

### WARRIOR_PRIEST_MAKE_AVAILABLE        = <TechInfo.WARRIOR_PRIEST_MAKE_AVAILABLE: (948, -1)>

### ELITE_QIZILBASH_WARRIOR        = <TechInfo.ELITE_QIZILBASH_WARRIOR: (967, 105)>

### SAVAR        = <TechInfo.SAVAR: (526, 130)>

### TECHNOLOGY_PLACEHOLDER_01        = <TechInfo.TECHNOLOGY_PLACEHOLDER_01: (968, 107)>

### TECHNOLOGY_PLACEHOLDER_02        = <TechInfo.TECHNOLOGY_PLACEHOLDER_02: (969, 107)>

### TECHNOLOGY_PLACEHOLDER_03        = <TechInfo.TECHNOLOGY_PLACEHOLDER_03: (970, 107)>

### TECHNOLOGY_PLACEHOLDER_04        = <TechInfo.TECHNOLOGY_PLACEHOLDER_04: (971, 107)>

### TECHNOLOGY_PLACEHOLDER_05        = <TechInfo.TECHNOLOGY_PLACEHOLDER_05: (972, 107)>

### TECHNOLOGY_PLACEHOLDER_06        = <TechInfo.TECHNOLOGY_PLACEHOLDER_06: (973, 107)>

### TECHNOLOGY_PLACEHOLDER_07        = <TechInfo.TECHNOLOGY_PLACEHOLDER_07: (974, 107)>

### TECHNOLOGY_PLACEHOLDER_08        = <TechInfo.TECHNOLOGY_PLACEHOLDER_08: (975, 107)>

### TECHNOLOGY_PLACEHOLDER_09        = <TechInfo.TECHNOLOGY_PLACEHOLDER_09: (976, 107)>

### TECHNOLOGY_PLACEHOLDER_10        = <TechInfo.TECHNOLOGY_PLACEHOLDER_10: (977, 107)>

### SPARABARAS        = <TechInfo.SPARABARAS: (1110, 164)>

### REED_ARROWS        = <TechInfo.REED_ARROWS: (1111, 165)>

### SCYTHED_CHARIOTS        = <TechInfo.SCYTHED_CHARIOTS: (1112, 166)>

### SAGARIS        = <TechInfo.SAGARIS: (1113, 167)>

### ELITE_IMMORTAL        = <TechInfo.ELITE_IMMORTAL: (1115, 105)>

### TAXIARCHS        = <TechInfo.TAXIARCHS: (1120, 164)>

### TRIERARCHIES        = <TechInfo.TRIERARCHIES: (1121, 165)>

### EISPHORA        = <TechInfo.EISPHORA: (1122, 166)>

### DELIAN_LEAGUE        = <TechInfo.DELIAN_LEAGUE: (1123, 167)>

### ELITE_STRATEGOS        = <TechInfo.ELITE_STRATEGOS: (1125, 105)>

### HELOT_LEVIES        = <TechInfo.HELOT_LEVIES: (1130, 164)>

### AGOGE        = <TechInfo.AGOGE: (1131, 166)>

### XYPHOS        = <TechInfo.XYPHOS: (1132, 165)>

### PELOPONNESIAN_LEAGUE        = <TechInfo.PELOPONNESIAN_LEAGUE: (1133, 167)>

### ELITE_HIPPEUS        = <TechInfo.ELITE_HIPPEUS: (1135, 105)>

### ELITE_HOPLITE        = <TechInfo.ELITE_HOPLITE: (1137, 188)>

### WAR_LEMBOS        = <TechInfo.WAR_LEMBOS: (1144, 190)>

### HEAVY_LEMBOS        = <TechInfo.HEAVY_LEMBOS: (1145, 191)>

### ELITE_LEMBOS        = <TechInfo.ELITE_LEMBOS: (1146, 192)>

### BIREME        = <TechInfo.BIREME: (1148, 193)>

### TRIREME        = <TechInfo.TRIREME: (1149, 194)>

### WAR_GALLEY_ANTIQUITY        = <TechInfo.WAR_GALLEY_ANTIQUITY: (1151, 195)>

### ELITE_GALLEY        = <TechInfo.ELITE_GALLEY: (1152, 196)>

### INCENDIARY_SHIP        = <TechInfo.INCENDIARY_SHIP: (1154, 39)>

### HEAVY_INCENDIARY_SHIP        = <TechInfo.HEAVY_INCENDIARY_SHIP: (1155, 250)>

### ONAGER_SHIP        = <TechInfo.ONAGER_SHIP: (1159, 197)>

### SCOOP_NETS        = <TechInfo.SCOOP_NETS: (1161, 41)>

### DRUMS        = <TechInfo.DRUMS: (1162, 99)>

### HYPOZOMATA        = <TechInfo.HYPOZOMATA: (1165, 169)>

### SHIPWRIGHT_ANTIQUITY        = <TechInfo.SHIPWRIGHT_ANTIQUITY: (1167, 97)>

### ELITE_WAR_CHARIOT        = <TechInfo.ELITE_WAR_CHARIOT: (1171, 184)>

### BATTLE_DRILLS        = <TechInfo.BATTLE_DRILLS: (1173, 168)>

### CHAMPION_ANTIQUITY        = <TechInfo.CHAMPION_ANTIQUITY: (1174, 183)>

### BLANK_TECHNOLOGY_0        = <TechInfo.BLANK_TECHNOLOGY_0: (1180, -1)>

### BLANK_TECHNOLOGY_1        = <TechInfo.BLANK_TECHNOLOGY_1: (1181, -1)>

### BLANK_TECHNOLOGY_2        = <TechInfo.BLANK_TECHNOLOGY_2: (1182, -1)>

### BLANK_TECHNOLOGY_3        = <TechInfo.BLANK_TECHNOLOGY_3: (1183, -1)>

### BLANK_TECHNOLOGY_4        = <TechInfo.BLANK_TECHNOLOGY_4: (1184, -1)>

### BLANK_TECHNOLOGY_5        = <TechInfo.BLANK_TECHNOLOGY_5: (1185, -1)>

### BLANK_TECHNOLOGY_6        = <TechInfo.BLANK_TECHNOLOGY_6: (1186, -1)>

### BLANK_TECHNOLOGY_7        = <TechInfo.BLANK_TECHNOLOGY_7: (1187, -1)>

### BLANK_TECHNOLOGY_8        = <TechInfo.BLANK_TECHNOLOGY_8: (1188, -1)>

### BLANK_TECHNOLOGY_9        = <TechInfo.BLANK_TECHNOLOGY_9: (1189, -1)>

### ECONOMIC_TOWN_CENTER        = <TechInfo.ECONOMIC_TOWN_CENTER: (<LocalTechnology.ECONOMIC_TOWN_CENTER: 1195>, 171)>

### MILITARY_TOWN_CENTER        = <TechInfo.MILITARY_TOWN_CENTER: (<LocalTechnology.MILITARY_TOWN_CENTER: 1196>, 170)>

### DEFENSIVE_TOWN_CENTER        = <TechInfo.DEFENSIVE_TOWN_CENTER: (<LocalTechnology.DEFENSIVE_TOWN_CENTER: 1197>, 172)>

### FREE_LEMBOS_SPAWN        = <TechInfo.FREE_LEMBOS_SPAWN: (1198, -1)>

### ECONOMIC_POLICY        = <TechInfo.ECONOMIC_POLICY: (1202, 155)>

### NAVAL_POLICY        = <TechInfo.NAVAL_POLICY: (1203, 156)>

### MILITARY_POLICY        = <TechInfo.MILITARY_POLICY: (1204, 154)>

### TRADE_25_PERCENT_WOOD_75_PERCENT_GOLD_PORT        = <TechInfo.TRADE_25_PERCENT_WOOD_75_PERCENT_GOLD_PORT: (1215, 158)>

### TRADE_50_PERCENT_WOOD_50_PERCENT_GOLD_PORT        = <TechInfo.TRADE_50_PERCENT_WOOD_50_PERCENT_GOLD_PORT: (1216, 157)>

### TRADE_75_PERCENT_WOOD_25_PERCENT_GOLD_PORT        = <TechInfo.TRADE_75_PERCENT_WOOD_25_PERCENT_GOLD_PORT: (1217, 159)>

### EPHORATE        = <TechInfo.EPHORATE: (1223, 163)>

### MORAI        = <TechInfo.MORAI: (1224, 162)>

### SKEUOPHOROI        = <TechInfo.SKEUOPHOROI: (1225, 160)>

### HIPPAGRETAI        = <TechInfo.HIPPAGRETAI: (1226, 161)>

### BLANK_TECHNOLOGY_10        = <TechInfo.BLANK_TECHNOLOGY_10: (1240, -1)>

### BLANK_TECHNOLOGY_11        = <TechInfo.BLANK_TECHNOLOGY_11: (1241, -1)>

### BLANK_TECHNOLOGY_12        = <TechInfo.BLANK_TECHNOLOGY_12: (1242, -1)>

### BLANK_TECHNOLOGY_13        = <TechInfo.BLANK_TECHNOLOGY_13: (1243, -1)>

### BLANK_TECHNOLOGY_14        = <TechInfo.BLANK_TECHNOLOGY_14: (1244, -1)>

### BLANK_TECHNOLOGY_15        = <TechInfo.BLANK_TECHNOLOGY_15: (1245, -1)>

### BLANK_TECHNOLOGY_16        = <TechInfo.BLANK_TECHNOLOGY_16: (1246, -1)>

### BLANK_TECHNOLOGY_17        = <TechInfo.BLANK_TECHNOLOGY_17: (1247, -1)>

### BLANK_TECHNOLOGY_18        = <TechInfo.BLANK_TECHNOLOGY_18: (1248, -1)>

### BLANK_TECHNOLOGY_19        = <TechInfo.BLANK_TECHNOLOGY_19: (1249, -1)>

### ACHAEMENIDS        = <TechInfo.ACHAEMENIDS: (1024, -1)>

### ATHENIANS        = <TechInfo.ATHENIANS: (1027, -1)>

### SPARTANS        = <TechInfo.SPARTANS: (1026, -1)>

### TRADE_0_PERCENT_WOOD_100_PERCENT_GOLD_TRADE_COG        = <TechInfo.TRADE_0_PERCENT_WOOD_100_PERCENT_GOLD_TRADE_COG: (1359, 94)>

### TRADE_25_PERCENT_WOOD_75_PERCENT_GOLD_TRADE_COG        = <TechInfo.TRADE_25_PERCENT_WOOD_75_PERCENT_GOLD_TRADE_COG: (1263, 158)>

### TRADE_50_PERCENT_WOOD_50_PERCENT_GOLD_TRADE_COG        = <TechInfo.TRADE_50_PERCENT_WOOD_50_PERCENT_GOLD_TRADE_COG: (1264, 157)>

### TRADE_75_PERCENT_WOOD_25_PERCENT_GOLD_TRADE_COG        = <TechInfo.TRADE_75_PERCENT_WOOD_25_PERCENT_GOLD_TRADE_COG: (1265, 159)>

### TRADE_100_PERCENT_WOOD_0_PERCENT_GOLD_TRADE_COG        = <TechInfo.TRADE_100_PERCENT_WOOD_0_PERCENT_GOLD_TRADE_COG: (1373, 95)>

### PIROTECHNIA        = <TechInfo.PIROTECHNIA: (902, 107)>

### HEAVY_ROCKET_CART        = <TechInfo.HEAVY_ROCKET_CART: (980, 133)>

### ELITE_FIRE_LANCER        = <TechInfo.ELITE_FIRE_LANCER: (982, 134)>

### ELITE_IRON_PAGODA        = <TechInfo.ELITE_IRON_PAGODA: (991, 105)>

### FORTIFIED_BASTIONS        = <TechInfo.FORTIFIED_BASTIONS: (996, 33)>

### THUNDERCLAP_BOMBS        = <TechInfo.THUNDERCLAP_BOMBS: (997, 107)>

### ELITE_LIAO_DAO        = <TechInfo.ELITE_LIAO_DAO: (1002, 105)>

### LAMELLAR_ARMOR        = <TechInfo.LAMELLAR_ARMOR: (1006, 33)>

### ORDO_CAVALRY        = <TechInfo.ORDO_CAVALRY: (1007, 107)>

### DRAGON_SHIP        = <TechInfo.DRAGON_SHIP: (1010, 40)>

### TRANSHUMANCE        = <TechInfo.TRANSHUMANCE: (1012, 136)>

### PASTORALISM        = <TechInfo.PASTORALISM: (1013, 137)>

### DOMESTICATION        = <TechInfo.DOMESTICATION: (1014, 138)>

### HEAVY_HEI_GUANG_CAVALRY        = <TechInfo.HEAVY_HEI_GUANG_CAVALRY: (1033, 132)>

### ELITE_TIGER_CAVALRY        = <TechInfo.ELITE_TIGER_CAVALRY: (1036, 105)>

### TUNTIAN        = <TechInfo.TUNTIAN: (1061, 33)>

### MING_GUANG_ARMOR        = <TechInfo.MING_GUANG_ARMOR: (1062, 107)>

### ELITE_WHITE_FEATHER_GUARD        = <TechInfo.ELITE_WHITE_FEATHER_GUARD: (1064, 105)>

### BOLT_MAGAZINE        = <TechInfo.BOLT_MAGAZINE: (1069, 107)>

### COILED_SERPENT_ARRAY        = <TechInfo.COILED_SERPENT_ARRAY: (1070, 33)>

### ELITE_FIRE_ARCHER        = <TechInfo.ELITE_FIRE_ARCHER: (1074, 105)>

### RED_CLIFFS_TACTICS        = <TechInfo.RED_CLIFFS_TACTICS: (1080, 33)>

### SITTING_TIGER        = <TechInfo.SITTING_TIGER: (1081, 107)>

### SHU        = <TechInfo.SHU: (1028, -1)>

### WU        = <TechInfo.WU: (1030, -1)>

### WEI        = <TechInfo.WEI: (1029, -1)>

### JURCHENS        = <TechInfo.JURCHENS: (986, -1)>

### KHITANS        = <TechInfo.KHITANS: (988, -1)>

### FORTIFIED_OUTPOST        = <TechInfo.FORTIFIED_OUTPOST: (<LocalTechnology.FORTIFIED_OUTPOST: 1270>, 309)>

### CONSCRIPT_RECRUITMENT_BARRACKS        = <TechInfo.CONSCRIPT_RECRUITMENT_BARRACKS: (1275, 207)>

### MERCENARY_RECRUITMENT_BARRACKS        = <TechInfo.MERCENARY_RECRUITMENT_BARRACKS: (1276, 209)>

### BALANCED_RECRUITMENT_BARRACKS        = <TechInfo.BALANCED_RECRUITMENT_BARRACKS: (1277, 208)>

### CONSCRIPT_RECRUITMENT_ARCHERY_RANGE        = <TechInfo.CONSCRIPT_RECRUITMENT_ARCHERY_RANGE: (1278, 207)>

### MERCENARY_RECRUITMENT_ARCHERY_RANGE        = <TechInfo.MERCENARY_RECRUITMENT_ARCHERY_RANGE: (1279, 209)>

### BALANCED_RECRUITMENT_ARCHERY_RANGE        = <TechInfo.BALANCED_RECRUITMENT_ARCHERY_RANGE: (1280, 208)>

### CONSCRIPT_RECRUITMENT_STABLE        = <TechInfo.CONSCRIPT_RECRUITMENT_STABLE: (1281, 207)>

### MERCENARY_RECRUITMENT_STABLE        = <TechInfo.MERCENARY_RECRUITMENT_STABLE: (1282, 209)>

### BALANCED_RECRUITMENT_STABLE        = <TechInfo.BALANCED_RECRUITMENT_STABLE: (1283, 208)>

### VETERAN_CHILIARCHS        = <TechInfo.VETERAN_CHILIARCHS: (1284, 164)>

### ENDS_OF_THE_WORLD        = <TechInfo.ENDS_OF_THE_WORLD: (1285, 165)>

### PEZHETAIROI        = <TechInfo.PEZHETAIROI: (1286, 166)>

### SARISSOPHOROI        = <TechInfo.SARISSOPHOROI: (1287, 167)>

### ELITE_COMPANION_CAVALRY        = <TechInfo.ELITE_COMPANION_CAVALRY: (1289, 105)>

### ELITE_PHALANGITE        = <TechInfo.ELITE_PHALANGITE: (1291, 105)>

### ODOMANTIAN_RAIDERS        = <TechInfo.ODOMANTIAN_RAIDERS: (1296, 164)>

### DII_PLUNDERERS        = <TechInfo.DII_PLUNDERERS: (1297, 165)>

### BESSIAN_METALWORKING        = <TechInfo.BESSIAN_METALWORKING: (1298, 166)>

### PELTASTS        = <TechInfo.PELTASTS: (1299, 167)>

### ELITE_RHOMPHAIA_WARRIOR        = <TechInfo.ELITE_RHOMPHAIA_WARRIOR: (1301, 105)>

### VADHAVADHA        = <TechInfo.VADHAVADHA: (1307, 164)>

### LEAF_HEADED_SHAFTS        = <TechInfo.LEAF_HEADED_SHAFTS: (1308, 165)>

### VEDIC_TEACHINGS        = <TechInfo.VEDIC_TEACHINGS: (1309, 166)>

### SKANDHAVARAS        = <TechInfo.SKANDHAVARAS: (1310, 167)>

### DEFENSIVE_EMPLACEMENT        = <TechInfo.DEFENSIVE_EMPLACEMENT: (<LocalTechnology.DEFENSIVE_EMPLACEMENT: 1323>, 300)>

### OFFENSIVE_EMPLACEMENT        = <TechInfo.OFFENSIVE_EMPLACEMENT: (<LocalTechnology.OFFENSIVE_EMPLACEMENT: 1324>, 301)>

### ELITE_PATTIYODHA_LONGBOWMAN        = <TechInfo.ELITE_PATTIYODHA_LONGBOWMAN: (1326, 105)>

### ELITE_SANNAHYA        = <TechInfo.ELITE_SANNAHYA: (1328, 105)>

### SC08_ALEXANDER_CUSTOM_TECH        = <TechInfo.SC08_ALEXANDER_CUSTOM_TECH: (1332, 299)>

### SC11_ALEXANDER_CUSTOM_TECH        = <TechInfo.SC11_ALEXANDER_CUSTOM_TECH: (1333, 299)>

### ELITE_SCYTHIAN_HORSE_ARCHER        = <TechInfo.ELITE_SCYTHIAN_HORSE_ARCHER: (1334, 52)>

### BLANK_TECHNOLOGY_20        = <TechInfo.BLANK_TECHNOLOGY_20: (1340, -1)>

### BLANK_TECHNOLOGY_21        = <TechInfo.BLANK_TECHNOLOGY_21: (1341, -1)>

### BLANK_TECHNOLOGY_22        = <TechInfo.BLANK_TECHNOLOGY_22: (1342, -1)>

### BLANK_TECHNOLOGY_23        = <TechInfo.BLANK_TECHNOLOGY_23: (1343, -1)>

### BLANK_TECHNOLOGY_24        = <TechInfo.BLANK_TECHNOLOGY_24: (1344, -1)>

### BLANK_TECHNOLOGY_25        = <TechInfo.BLANK_TECHNOLOGY_25: (1345, -1)>

### BLANK_TECHNOLOGY_26        = <TechInfo.BLANK_TECHNOLOGY_26: (1346, -1)>

### BLANK_TECHNOLOGY_27        = <TechInfo.BLANK_TECHNOLOGY_27: (1347, -1)>

### BLANK_TECHNOLOGY_28        = <TechInfo.BLANK_TECHNOLOGY_28: (1348, -1)>

### BLANK_TECHNOLOGY_29        = <TechInfo.BLANK_TECHNOLOGY_29: (1349, -1)>

### BLANK_TECHNOLOGY_30        = <TechInfo.BLANK_TECHNOLOGY_30: (1500, -1)>

### BLANK_TECHNOLOGY_31        = <TechInfo.BLANK_TECHNOLOGY_31: (1501, -1)>

### BLANK_TECHNOLOGY_32        = <TechInfo.BLANK_TECHNOLOGY_32: (1502, -1)>

### BLANK_TECHNOLOGY_33        = <TechInfo.BLANK_TECHNOLOGY_33: (1503, -1)>

### BLANK_TECHNOLOGY_34        = <TechInfo.BLANK_TECHNOLOGY_34: (1504, -1)>

### BLANK_TECHNOLOGY_35        = <TechInfo.BLANK_TECHNOLOGY_35: (1505, -1)>

### BLANK_TECHNOLOGY_36        = <TechInfo.BLANK_TECHNOLOGY_36: (1506, -1)>

### BLANK_TECHNOLOGY_37        = <TechInfo.BLANK_TECHNOLOGY_37: (1507, -1)>

### BLANK_TECHNOLOGY_38        = <TechInfo.BLANK_TECHNOLOGY_38: (1508, -1)>

### BLANK_TECHNOLOGY_39        = <TechInfo.BLANK_TECHNOLOGY_39: (1509, -1)>

### DEMOLITION_SHIP        = <TechInfo.DEMOLITION_SHIP: (905, 139)>

### FISHING_LINES        = <TechInfo.FISHING_LINES: (906, 140)>

### CARVEL_HULL        = <TechInfo.CARVEL_HULL: (907, 141)>

### CLINKER_CONSTRUCTION        = <TechInfo.CLINKER_CONSTRUCTION: (908, 142)>

### SIPHONS        = <TechInfo.SIPHONS: (909, 40)>

### INCENDIARIES        = <TechInfo.INCENDIARIES: (910, 143)>

### CHAMPI_SCOUT_MAKE_AVAILABLE        = <TechInfo.CHAMPI_SCOUT_MAKE_AVAILABLE: (1350, 75)>

### CHAMPI_WARRIOR        = <TechInfo.CHAMPI_WARRIOR: (1351, 144)>

### ELITE_CHAMPI_WARRIOR        = <TechInfo.ELITE_CHAMPI_WARRIOR: (1352, 145)>

### ELITE_GUECHA_WARRIOR        = <TechInfo.ELITE_GUECHA_WARRIOR: (1364, 105)>

### HERBALISM        = <TechInfo.HERBALISM: (1365, 33)>

### HUARACAS        = <TechInfo.HUARACAS: (1366, 107)>

### ELITE_KONA        = <TechInfo.ELITE_KONA: (1376, 105)>

### ELITE_BOLAS_RIDER        = <TechInfo.ELITE_BOLAS_RIDER: (1378, 105)>

### MALON        = <TechInfo.MALON: (1379, 33)>

### BUTALMAPU        = <TechInfo.BUTALMAPU: (1380, 107)>

### ELITE_WAR_DOG        = <TechInfo.ELITE_WAR_DOG: (1387, 149)>

### ELITE_BLACKWOOD_ARCHER        = <TechInfo.ELITE_BLACKWOOD_ARCHER: (1389, 105)>

### ELITE_IBIRAPEMA_WARRIOR        = <TechInfo.ELITE_IBIRAPEMA_WARRIOR: (1391, 105)>

### CACIQUES        = <TechInfo.CACIQUES: (1392, 33)>

### CURARE        = <TechInfo.CURARE: (1393, 107)>

### ELITE_TEMPLE_GUARD        = <TechInfo.ELITE_TEMPLE_GUARD: (1401, 105)>

### CHAMPI_RUNNER        = <TechInfo.CHAMPI_RUNNER: (1402, 146)>

### CIRCUMNAVIGATION        = <TechInfo.CIRCUMNAVIGATION: (1404, 33)>

### MACEDONIANS        = <TechInfo.MACEDONIANS: (1268, -1)>

### THRACIANS        = <TechInfo.THRACIANS: (1292, -1)>

### PURU        = <TechInfo.PURU: (1302, -1)>

### MAPUCHE        = <TechInfo.MAPUCHE: (1361, -1)>

### MUISCA        = <TechInfo.MUISCA: (1360, -1)>

### TUPI        = <TechInfo.TUPI: (1362, -1)>

### HEAVY_MOUNTED_CROSSBOWMAN        = <TechInfo.HEAVY_MOUNTED_CROSSBOWMAN: (1451, 77)>

### CRANEQUINS        = <TechInfo.CRANEQUINS: (1452, 56)>

### ELITE_VARANGIAN_GUARD        = <TechInfo.ELITE_VARANGIAN_GUARD: (1454, 72)>

### SAXONS        = <TechInfo.SAXONS: (1458, -1)>

### VARANGIANS        = <TechInfo.VARANGIANS: (1459, -1)>

### DANES        = <TechInfo.DANES: (1460, -1)>

### ELITE_HEARTH_TROOP        = <TechInfo.ELITE_HEARTH_TROOP: (1462, 105)>

### SHIELD_WALL        = <TechInfo.SHIELD_WALL: (1464, 107)>

### ELITE_JARL        = <TechInfo.ELITE_JARL: (1472, 105)>

### VENDEL_LEGACY        = <TechInfo.VENDEL_LEGACY: (1473, 33)>

### GOTHIKON        = <TechInfo.GOTHIKON: (1474, 107)>

### ELITE_JOMSVIKING        = <TechInfo.ELITE_JOMSVIKING: (1482, 105)>

### NORTHMENS_FURY        = <TechInfo.NORTHMENS_FURY: (1483, 107)>

### HAMASK        = <TechInfo.HAMASK: (1484, 33)>

### CLERICAL_RECRUITMENT        = <TechInfo.CLERICAL_RECRUITMENT: (1491, 33)>

### ORDONNANCE_COMPANIES        = <TechInfo.ORDONNANCE_COMPANIES: (1496, 33)>


### class     TerrainId(enum.IntEnum):
This enum class provides information about most of the terrains in the game. Information about the
following properties of a terrain is found in this class:

- Terrain ID

Methods

Examples

### @staticmethod
Returns:
    A list of all Water terrains

### @staticmethod
Returns:
    A list of all Beach terrains

### @staticmethod
Returns:
    A list of all Tree terrains

### BEACH        = <TerrainId.BEACH: 2>

### BEACH_NON_NAVIGABLE        = <TerrainId.BEACH_NON_NAVIGABLE: 79>

### BEACH_NON_NAVIGABLE_WET_GRAVEL        = <TerrainId.BEACH_NON_NAVIGABLE_WET_GRAVEL: 81>

### BEACH_NON_NAVIGABLE_WET_ROCK        = <TerrainId.BEACH_NON_NAVIGABLE_WET_ROCK: 82>

### BEACH_NON_NAVIGABLE_WET_SAND        = <TerrainId.BEACH_NON_NAVIGABLE_WET_SAND: 80>

### BEACH_ICE        = <TerrainId.BEACH_ICE: 37>

### BEACH_VEGETATION        = <TerrainId.BEACH_VEGETATION: 52>

### BEACH_WET        = <TerrainId.BEACH_WET: 107>

### BEACH_WET_GRAVEL        = <TerrainId.BEACH_WET_GRAVEL: 108>

### BEACH_WET_ROCK        = <TerrainId.BEACH_WET_ROCK: 109>

### BEACH_WHITE        = <TerrainId.BEACH_WHITE: 53>

### BEACH_WHITE_VEGETATION        = <TerrainId.BEACH_WHITE_VEGETATION: 51>

### BLACK        = <TerrainId.BLACK: 47>

### DESERT_CRACKED        = <TerrainId.DESERT_CRACKED: 45>

### DESERT_QUICKSAND        = <TerrainId.DESERT_QUICKSAND: 46>

### DESERT_SAND        = <TerrainId.DESERT_SAND: 14>

### DIRT_1        = <TerrainId.DIRT_1: 6>

### DIRT_2        = <TerrainId.DIRT_2: 11>

### DIRT_3        = <TerrainId.DIRT_3: 3>

### DIRT_4        = <TerrainId.DIRT_4: 42>

### DIRT_MUD        = <TerrainId.DIRT_MUD: 76>

### DIRT_SAVANNAH        = <TerrainId.DIRT_SAVANNAH: 41>

### FARM        = <TerrainId.FARM: 7>

### FARM_0        = <TerrainId.FARM_0: 29>

### FARM_33        = <TerrainId.FARM_33: 30>

### FARM_67        = <TerrainId.FARM_67: 31>

### FARM_DEAD        = <TerrainId.FARM_DEAD: 8>

### FOREST_ACACIA        = <TerrainId.FOREST_ACACIA: 50>

### FOREST_AUTUMN        = <TerrainId.FOREST_AUTUMN: 104>

### FOREST_AUTUMN_SNOW        = <TerrainId.FOREST_AUTUMN_SNOW: 105>

### FOREST_BAMBOO        = <TerrainId.FOREST_BAMBOO: 18>

### FOREST_BAOBAB        = <TerrainId.FOREST_BAOBAB: 49>

### FOREST_BIRCH        = <TerrainId.FOREST_BIRCH: 110>

### FOREST_BUSH        = <TerrainId.FOREST_BUSH: 89>

### FOREST_DEAD        = <TerrainId.FOREST_DEAD: 106>

### FOREST_DRAGON_TREE        = <TerrainId.FOREST_DRAGON_TREE: 48>

### FOREST_JUNGLE        = <TerrainId.FOREST_JUNGLE: 17>

### FOREST_MANGROVE        = <TerrainId.FOREST_MANGROVE: 55>

### FOREST_MEDITERRANEAN        = <TerrainId.FOREST_MEDITERRANEAN: 88>

### FOREST_OAK        = <TerrainId.FOREST_OAK: 10>

### FOREST_OAK_BUSH        = <TerrainId.FOREST_OAK_BUSH: 20>

### FOREST_PALM_DESERT        = <TerrainId.FOREST_PALM_DESERT: 13>

### FOREST_PINE        = <TerrainId.FOREST_PINE: 19>

### FOREST_PINE_SNOW        = <TerrainId.FOREST_PINE_SNOW: 21>

### FOREST_RAINFOREST        = <TerrainId.FOREST_RAINFOREST: 56>

### FOREST_REEDS        = <TerrainId.FOREST_REEDS: 92>

### FOREST_REEDS_BEACH        = <TerrainId.FOREST_REEDS_BEACH: 91>

### FOREST_REEDS_SHALLOWS        = <TerrainId.FOREST_REEDS_SHALLOWS: 90>

### GRASS_1        = <TerrainId.GRASS_1: 0>

### GRASS_2        = <TerrainId.GRASS_2: 12>

### GRASS_3        = <TerrainId.GRASS_3: 9>

### GRASS_DRY        = <TerrainId.GRASS_DRY: 100>

### GRASS_FOUNDATION        = <TerrainId.GRASS_FOUNDATION: 27>

### GRASS_JUNGLE        = <TerrainId.GRASS_JUNGLE: 60>

### GRASS_JUNGLE_RAINFOREST        = <TerrainId.GRASS_JUNGLE_RAINFOREST: 83>

### GRASS_OTHER        = <TerrainId.GRASS_OTHER: 16>

### GRAVEL_DEFAULT        = <TerrainId.GRAVEL_DEFAULT: 70>

### GRAVEL_DESERT        = <TerrainId.GRAVEL_DESERT: 102>

### ICE        = <TerrainId.ICE: 35>

### ICE_NAVIGABLE        = <TerrainId.ICE_NAVIGABLE: 26>

### MODDABLE_GRASS_1        = <TerrainId.MODDABLE_GRASS_1: 84>

### MODDABLE_GRASS_2        = <TerrainId.MODDABLE_GRASS_2: 85>

### MODDABLE_GRASS_3        = <TerrainId.MODDABLE_GRASS_3: 86>

### MODDABLE_GRASS_4        = <TerrainId.MODDABLE_GRASS_4: 87>

### MODDABLE_DEEP_WATER        = <TerrainId.MODDABLE_DEEP_WATER: 99>

### MODDABLE_NORMAL_WATER_1        = <TerrainId.MODDABLE_NORMAL_WATER_1: 97>

### MODDABLE_NORMAL_WATER_2        = <TerrainId.MODDABLE_NORMAL_WATER_2: 98>

### MODDABLE_SHALLOWS_1        = <TerrainId.MODDABLE_SHALLOWS_1: 93>

### MODDABLE_SHALLOWS_2        = <TerrainId.MODDABLE_SHALLOWS_2: 94>

### OBSOLETE_UNDERBRUSH_JUNGLE        = <TerrainId.OBSOLETE_UNDERBRUSH_JUNGLE: 62>

### OBSOLETE_ROAD_DESERT        = <TerrainId.OBSOLETE_ROAD_DESERT: 43>

### OBSOLETE_ROAD_FUNGUS        = <TerrainId.OBSOLETE_ROAD_FUNGUS: 39>

### OBSOLETE_ROAD_GRAVEL        = <TerrainId.OBSOLETE_ROAD_GRAVEL: 103>

### OBSOLETE_ROAD_JUNGLE        = <TerrainId.OBSOLETE_ROAD_JUNGLE: 61>

### OBSOLETE_ROAD_SNOW        = <TerrainId.OBSOLETE_ROAD_SNOW: 38>

### OBSOLETE_SNOW_DIRT        = <TerrainId.OBSOLETE_SNOW_DIRT: 33>

### OBSOLETE_SNOW_GRASS        = <TerrainId.OBSOLETE_SNOW_GRASS: 34>

### RESERVED        = <TerrainId.RESERVED: 68>

### RICE_FARM        = <TerrainId.RICE_FARM: 63>

### RICE_FARM_0        = <TerrainId.RICE_FARM_0: 65>

### RICE_FARM_33        = <TerrainId.RICE_FARM_33: 66>

### RICE_FARM_67        = <TerrainId.RICE_FARM_67: 67>

### RICE_FARM_DEAD        = <TerrainId.RICE_FARM_DEAD: 64>

### ROAD        = <TerrainId.ROAD: 24>

### ROAD_BROKEN        = <TerrainId.ROAD_BROKEN: 25>

### ROAD_FUNGUS        = <TerrainId.ROAD_FUNGUS: 75>

### ROAD_GRAVEL        = <TerrainId.ROAD_GRAVEL: 78>

### ROCK_1        = <TerrainId.ROCK_1: 40>

### SHALLOWS        = <TerrainId.SHALLOWS: 4>

### SHALLOWS_AZURE        = <TerrainId.SHALLOWS_AZURE: 59>

### SHALLOWS_MANGROVE        = <TerrainId.SHALLOWS_MANGROVE: 54>

### SNOW        = <TerrainId.SNOW: 32>

### SNOW_FOUNDATION        = <TerrainId.SNOW_FOUNDATION: 36>

### SNOW_LIGHT        = <TerrainId.SNOW_LIGHT: 73>

### SNOW_STRONG        = <TerrainId.SNOW_STRONG: 74>

### SWAMP_SHALLOWS        = <TerrainId.SWAMP_SHALLOWS: 111>

### SWAMP_BOGLAND        = <TerrainId.SWAMP_BOGLAND: 101>

### UNDERBRUSH        = <TerrainId.UNDERBRUSH: 5>

### UNDERBRUSH_JUNGLE        = <TerrainId.UNDERBRUSH_JUNGLE: 77>

### UNDERBRUSH_LEAVES        = <TerrainId.UNDERBRUSH_LEAVES: 71>

### UNDERBRUSH_SNOW        = <TerrainId.UNDERBRUSH_SNOW: 72>

### CORRUPTION        = <TerrainId.CORRUPTION: 69>

### WATER_2D_BRIDGE        = <TerrainId.WATER_2D_BRIDGE: 28>

### WATER_2D_SHORELESS        = <TerrainId.WATER_2D_SHORELESS: 15>

### WATER_AZURE        = <TerrainId.WATER_AZURE: 58>

### WATER_BROWN        = <TerrainId.WATER_BROWN: 96>

### WATER_DEEP        = <TerrainId.WATER_DEEP: 22>

### WATER_DEEP_OCEAN        = <TerrainId.WATER_DEEP_OCEAN: 57>

### WATER_GREEN        = <TerrainId.WATER_GREEN: 95>

### WATER_MEDIUM        = <TerrainId.WATER_MEDIUM: 23>

### WATER_SHALLOW        = <TerrainId.WATER_SHALLOW: 1>

### OBSOLETE_DIRT_MUD        = <TerrainId.OBSOLETE_DIRT_MUD: 44>

### FOREST_PALM_GRASS        = <TerrainId.FOREST_PALM_GRASS: 112>

### FOREST_LUSH_BAMBOO        = <TerrainId.FOREST_LUSH_BAMBOO: 113>

### WATER_YELLOW_SHALLOW        = <TerrainId.WATER_YELLOW_SHALLOW: 114>

### SHALLOWS_YELLOW        = <TerrainId.SHALLOWS_YELLOW: 115>

### WATER_YELLOW_DEEP        = <TerrainId.WATER_YELLOW_DEEP: 116>

### PASTURE        = <TerrainId.PASTURE: 117>

### PASTURE_DEAD        = <TerrainId.PASTURE_DEAD: 118>

### PASTURE_0        = <TerrainId.PASTURE_0: 119>

### PASTURE_33        = <TerrainId.PASTURE_33: 120>

### PASTURE_67        = <TerrainId.PASTURE_67: 121>

### GRASS_FLOWERS_1        = <TerrainId.GRASS_FLOWERS_1: 122>

### GRASS_FLOWERS_2        = <TerrainId.GRASS_FLOWERS_2: 123>

### SNOW_SOFT        = <TerrainId.SNOW_SOFT: 124>

### SNOW_SOFT_LIGHT        = <TerrainId.SNOW_SOFT_LIGHT: 125>

### SNOW_SOFT_STRONG        = <TerrainId.SNOW_SOFT_STRONG: 126>

### ICE_SOFT        = <TerrainId.ICE_SOFT: 127>

### BLACK_WALKABLE        = <TerrainId.BLACK_WALKABLE: 129>

### FOREST_DRY_SOUTH_AMERICAN        = <TerrainId.FOREST_DRY_SOUTH_AMERICAN: 128>

### WATER_WEEDS        = <TerrainId.WATER_WEEDS: 130>

### FOREST_SPRUCE        = <TerrainId.FOREST_SPRUCE: 131>

### FOREST_SPRUCE_SNOW        = <TerrainId.FOREST_SPRUCE_SNOW: 132>

### FOREST_OAK_GREEN        = <TerrainId.FOREST_OAK_GREEN: 133>


### datasets/trigger_lists


### class     ActionType(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the different action types in the game.
These values are used in the Task Object effect

Examples

### DEFAULT        = <ActionType.DEFAULT: 0>

### MOVE        = <ActionType.MOVE: 1>

### PATROL        = <ActionType.PATROL: 2>

### GUARD        = <ActionType.GUARD: 3>

### FOLLOW        = <ActionType.FOLLOW: 4>

### STOP        = <ActionType.STOP: 5>

### ATTACK_GROUND        = <ActionType.ATTACK_GROUND: 6>

### GARRISON        = <ActionType.GARRISON: 7>

### KILL        = <ActionType.KILL: 8>

### UNLOAD        = <ActionType.UNLOAD: 9>

### GATHER_POINT        = <ActionType.GATHER_POINT: 10>

### LOCK_UNLOCK        = <ActionType.LOCK_UNLOCK: 11>

### WORK        = <ActionType.WORK: 12>

### UNGARRISON        = <ActionType.UNGARRISON: 13>

### DROP_RELIC        = <ActionType.DROP_RELIC: 14>

### PACK        = <ActionType.PACK: 15>

### UNPACK        = <ActionType.UNPACK: 16>

### ATTACK_MOVE        = <ActionType.ATTACK_MOVE: 17>

### LINE_FORMATION        = <ActionType.LINE_FORMATION: 18>

### BOX_FORMATION        = <ActionType.BOX_FORMATION: 19>

### STAGGERED_FORMATION        = <ActionType.STAGGERED_FORMATION: 20>

### FLANK_FORMATION        = <ActionType.FLANK_FORMATION: 21>

### TRANSFORM        = <ActionType.TRANSFORM: 22>

### SELL_FOOD        = <ActionType.SELL_FOOD: 23>

### SELL_WOOD        = <ActionType.SELL_WOOD: 24>

### SELL_STONE        = <ActionType.SELL_STONE: 25>

### BUY_FOOD        = <ActionType.BUY_FOOD: 26>

### BUY_WOOD        = <ActionType.BUY_WOOD: 27>

### BUY_STONE        = <ActionType.BUY_STONE: 28>

### RING_TOWN_BELL        = <ActionType.RING_TOWN_BELL: 29>

### BACK_TO_WORK        = <ActionType.BACK_TO_WORK: 30>

### ALL_BACK_TO_WORK        = <ActionType.ALL_BACK_TO_WORK: 31>

### FORCE_DROP_OFF        = <ActionType.FORCE_DROP_OFF: 32>


### class     Age(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the different ages in the game. These values are
used by the 'Current Age' player resource

Examples

### DARK_AGE        = <Age.DARK_AGE: 0>

### FEUDAL_AGE        = <Age.FEUDAL_AGE: 1>

### CASTLE_AGE        = <Age.CASTLE_AGE: 2>

### IMPERIAL_AGE        = <Age.IMPERIAL_AGE: 3>


### class     AttackPriority(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the attack priority values used in the game. Used in the
'Modify Attribute' effect with the 'Attack Priority' attributes

Examples

### UNITS_BEFORE_BUILDINGS        = <AttackPriority.UNITS_BEFORE_BUILDINGS: 1>

### BUILDINGS_BEFORE_UNITS        = <AttackPriority.BUILDINGS_BEFORE_UNITS: 2>

### BUILDINGS_ONLY        = <AttackPriority.BUILDINGS_ONLY: 3>


### class     AttackStance(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the different unit stances in the game. Used in the
'Change Object Stance' effect

Examples

### AGGRESSIVE_STANCE        = <AttackStance.AGGRESSIVE_STANCE: 0>

### DEFENSIVE_STANCE        = <AttackStance.DEFENSIVE_STANCE: 1>

### STAND_GROUND        = <AttackStance.STAND_GROUND: 2>

### NO_ATTACK_STANCE        = <AttackStance.NO_ATTACK_STANCE: 3>


### class     Attribute(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference all the player resources in the game. Used in effects
and conditions like 'Accumulate Attribute' and 'Modify Resource'

Examples

You can also request the editor names of these player attributes (resources) to be used in <...> notation in
trigger displays using:

### editor_name: str | None
The exact name of this resource in the editor. To be used in <...> notation in trigger displays

### FOOD_STORAGE        = <Attribute.FOOD_STORAGE: 0>
- Purpose: Current food amount

### WOOD_STORAGE        = <Attribute.WOOD_STORAGE: 1>
- Purpose: Current wood amount

### STONE_STORAGE        = <Attribute.STONE_STORAGE: 2>
- Purpose: Current stone amount

### GOLD_STORAGE        = <Attribute.GOLD_STORAGE: 3>
- Purpose: Current gold amount

### POPULATION_HEADROOM        = <Attribute.POPULATION_HEADROOM: 4>
- Purpose: Amount of free population space. Note that this is NOT the population cap

### CONVERSION_RANGE        = <Attribute.CONVERSION_RANGE: 5>
- Purpose: Unknown... What does this resource do?

### CURRENT_AGE        = <Attribute.CURRENT_AGE: 6>
- Purpose: Controls the age name and icon at the top of the screen

- Defaults:

- 0: Dark Age

- 1: Feudal Age

- 2: Castle Age

- 3: Imperial Age

- Note: Setting this to an amount higher than 3 cycles the icon but keeps the age at imperial

### RELICS_CAPTURED        = <Attribute.RELICS_CAPTURED: 7>
- Purpose: Number of relics held

### ENABLE_SUN_CE_BUILDING_CONVERSION_UNUSED_RESOURCE_08        = <Attribute.ENABLE_SUN_CE_BUILDING_CONVERSION_UNUSED_RESOURCE_08: 8>
- Purpose: Enables Sun Ce to convert buildings

- Defaults:

- 0: No (default)

- 1: Yes

- >=2: Sun Ce can convert buildings from range

- Note: The editor name of the resource is incorrect

### TRADE_GOODS        = <Attribute.TRADE_GOODS: 9>
- Purpose: Unused

### UNUSED_RESOURCE_10        = <Attribute.UNUSED_RESOURCE_10: 10>
- Purpose: Unused

### CURRENT_POPULATION        = <Attribute.CURRENT_POPULATION: 11>
- Purpose: The current population

### CORPSE_DECAY_TIME        = <Attribute.CORPSE_DECAY_TIME: 12>
- Purpose: Unknown... What does this resource do?

### REMARKABLE_DISCOVERY        = <Attribute.REMARKABLE_DISCOVERY: 13>
- Purpose: Unknown... What does this resource do?

### MONUMENTS_CAPTURED        = <Attribute.MONUMENTS_CAPTURED: 14>
- Purpose: Number of monuments owned

### MEAT_STORAGE        = <Attribute.MEAT_STORAGE: 15>
- Purpose: Unknown... What does this resource do?

### BERRY_STORAGE        = <Attribute.BERRY_STORAGE: 16>
- Purpose: Unknown... What does this resource do?

### FISH_STORAGE        = <Attribute.FISH_STORAGE: 17>
- Purpose: Unknown... What does this resource do?

### CIVILIZATION_VOICE_OVERRIDE        = <Attribute.CIVILIZATION_VOICE_OVERRIDE: 18>
- Purpose: Allows overriding a civilization's voice lines with another civ

### TOTAL_UNITS_OWNED        = <Attribute.TOTAL_UNITS_OWNED: 19>
- Purpose: Total units owned, excluding buildings

### UNITS_KILLED        = <Attribute.UNITS_KILLED: 20>
- Purpose: Total units killed, excluding buildings

### TECHNOLOGY_COUNT        = <Attribute.TECHNOLOGY_COUNT: 21>
- Purpose: Number of technologies researched till now

### PERCENT_MAP_EXPLORED        = <Attribute.PERCENT_MAP_EXPLORED: 22>
- Purpose: Percentage of the map explored

### CASTLE_AGE_TECH_ID        = <Attribute.CASTLE_AGE_TECH_ID: 23>
- Purpose: Always 102

- Note: Nothing happens when you change this, probably for mods only

### IMPERIAL_AGE_TECH_ID        = <Attribute.IMPERIAL_AGE_TECH_ID: 24>
- Purpose: Always 103

- Note: Nothing happens when you change this, probably for mods only

### FEUDAL_AGE_TECH_ID        = <Attribute.FEUDAL_AGE_TECH_ID: 25>
- Purpose: Always 101

- Note: Nothing happens when you change this, probably for mods only

### ATTACK_WARNING_SOUND_ID        = <Attribute.ATTACK_WARNING_SOUND_ID: 26>
- Purpose: Always 0

- Note: Nothing happens when you change this, probably for mods only

### ENABLE_MONK_CONVERSION        = <Attribute.ENABLE_MONK_CONVERSION: 27>
- Purpose: Boolean: allow enemy monk conversions

- Defaults:

- 0: No (default)

- >= 1: Yes, after Atonement

### ENABLE_BUILDING_CONVERSION        = <Attribute.ENABLE_BUILDING_CONVERSION: 28>
- Purpose: Boolean: allow enemy building conversions

- Defaults:

- 0: No (default)

- 1: Yes, after Redemption

- >=2: Monks can convert buildings from range

### ENABLE_SIEGE_CONVERSION        = <Attribute.ENABLE_SIEGE_CONVERSION: 29>
- Purpose: Boolean: allow enemy siege conversions

- Defaults:

- 0: No (default)

- 1: Yes, after Redemption

- >=2: Monks can convert siege from range

### UNUSED_RESOURCE_030        = <Attribute.UNUSED_RESOURCE_030: 30>
- Purpose: This resource is unused but is known to sometimes have some values. Use with caution

### UNUSED_RESOURCE_031        = <Attribute.UNUSED_RESOURCE_031: 31>
- Purpose: This resource is unused but is known to sometimes have some values. Use with caution

### BONUS_POPULATION_CAP        = <Attribute.BONUS_POPULATION_CAP: 32>
- Purpose: Additional pop space to grant on top of maximum pop cap

- Note: 10 for goths

### EFFECT_FUNCTION_NUMBER        = <Attribute.EFFECT_FUNCTION_NUMBER: 33>
- Purpose: Used to invoke functions in XS from data. When set to a non zero value N, it will automatically call a function named EffectFunctionN from the Effects.xs file.

### UNUSED_RESOURCE_034        = <Attribute.UNUSED_RESOURCE_034: 34>
- Purpose: This resource is unused but is known to sometimes have some values. Use with caution

### UNUSED_RESOURCE_035        = <Attribute.UNUSED_RESOURCE_035: 35>
- Purpose: This resource is unused but is known to sometimes have some values. Use with caution

### FARM_FOOD_AMOUNT        = <Attribute.FARM_FOOD_AMOUNT: 36>
- Purpose: Maximum farm food amount

- Defaults:

- 175: Default

- 220: Chinese

- Note: This is what horse collar etc. technologies modify

### CIVILIAN_POPULATION        = <Attribute.CIVILIAN_POPULATION: 37>
- Purpose: Current civilian population

### VILLAGER_POPULATION        = <Attribute.VILLAGER_POPULATION: 38>
- Purpose: Current villager population

### ALL_TECHS_ACHIEVED        = <Attribute.ALL_TECHS_ACHIEVED: 39>
- Purpose: Boolean: If all available technologies have been researched

- Defaults:

- 0: No

- 1: Yes

### MILITARY_POPULATION        = <Attribute.MILITARY_POPULATION: 40>
- Purpose: Current military popupation

### CONVERSIONS        = <Attribute.CONVERSIONS: 41>
- Purpose: Number of units converted

### STANDING_WONDERS        = <Attribute.STANDING_WONDERS: 42>
- Purpose: Number of standing wonders

### RAZINGS        = <Attribute.RAZINGS: 43>
- Purpose: Number of buildings razed

### KILL_RATIO        = <Attribute.KILL_RATIO: 44>
- Purpose: This is the number of units lost subtracted from the number of units killed in total

### SURVIVAL_TO_FINISH        = <Attribute.SURVIVAL_TO_FINISH: 45>
- Purpose: Boolean: This is set to 0 under the same conditions which are required to defeat a player

- Defaults:

- 0: No

- 1: Yes

### TRIBUTE_INEFFICIENCY        = <Attribute.TRIBUTE_INEFFICIENCY: 46>
- Purpose: This is the fraction of tributes sent that are collected as tax

- Defaults:

- 0.3: Default

- 0.2: After Coinage

- 0: After Banking

### GOLD_MINING_PRODUCTIVITY        = <Attribute.GOLD_MINING_PRODUCTIVITY: 47>
- Purpose: Multiplier for gold mined by gold miners

- Defaults:

- 1: Default

- 1.15: Mayans

- Note: Since this works by multiplying the amount of resources gathered by a villager, it has a side effect of increasing the gather rate. In the case of Mayans, This is compensated for by reducing villager work rate by 15%

### TOWN_CENTER_UNAVAILABLE        = <Attribute.TOWN_CENTER_UNAVAILABLE: 48>
- Purpose: Boolean: allow building extra tcs

- Defaults:

- 0: No (Sudden Death)

- 1: Yes (Normal)

### GOLD_COUNTER        = <Attribute.GOLD_COUNTER: 49>
- Purpose: Total gold collected

### REVEAL_ALLY        = <Attribute.REVEAL_ALLY: 50>
- Purpose: Boolean: show ally los for the source player

- Defaults:

- 0: No (default)

- 1: Yes, after Cartography or with a Portuguese ally

- Note: Once set to 1, setting it back to 0 won't take away the LoS of allies

### UNUSED_RESOURCE_051        = <Attribute.UNUSED_RESOURCE_051: 51>
- Purpose: Unused

### MONASTERIES        = <Attribute.MONASTERIES: 52>
- Purpose: Number of monasteries

### TRIBUTE_SENT        = <Attribute.TRIBUTE_SENT: 53>
- Purpose: Total of all resources tributed to others. This does not count taxes paid on tributing

### ALL_MONUMENTS_CAPTURED        = <Attribute.ALL_MONUMENTS_CAPTURED: 54>
- Purpose: Boolean: all monuments on the map captured

- Defaults:

- 0: No

- 1: Yes

### ALL_RELICS_CAPTURED        = <Attribute.ALL_RELICS_CAPTURED: 55>
- Purpose: Boolean: all relics on the map captured

- Defaults:

- 0: No

- 1: Yes

### ORE_STORAGE        = <Attribute.ORE_STORAGE: 56>
- Purpose: Unused

### KIDNAP_STORAGE        = <Attribute.KIDNAP_STORAGE: 57>
- Purpose: Number of units kidnapped

- Note: This is probably only used by mods, this usage may be incorrect

### DARK_AGE_TECH_ID        = <Attribute.DARK_AGE_TECH_ID: 58>
- Purpose: Always 104

- Note: Nothing happens when you change this

### UNUSED_RESOURCE_059        = <Attribute.UNUSED_RESOURCE_059: 59>
- Purpose: This resource is unused but is known to sometimes have some values. Use with caution

### UNUSED_RESOURCE_060        = <Attribute.UNUSED_RESOURCE_060: 60>
- Purpose: This resource is unused but is known to sometimes have some values. Use with caution

### UNUSED_RESOURCE_061        = <Attribute.UNUSED_RESOURCE_061: 61>
- Purpose: Unused

### BUILDING_HOUSING_RATE        = <Attribute.BUILDING_HOUSING_RATE: 62>
- Purpose: Unknown... What does this resource do?

### TAX_GATHER_RATE        = <Attribute.TAX_GATHER_RATE: 63>
- Purpose: Unknown... What does this resource do?

### GATHER_ACCUMULATOR        = <Attribute.GATHER_ACCUMULATOR: 64>
- Purpose: Unknown... What does this resource do?

### SALVAGE_DECAY_RATE        = <Attribute.SALVAGE_DECAY_RATE: 65>
- Purpose: Unknown... What does this resource do?

### UNUSED_RESOURCE_066        = <Attribute.UNUSED_RESOURCE_066: 66>
- Purpose: This resource is unused but is known to sometimes have some values. Use with caution

### CAN_CONVERT        = <Attribute.CAN_CONVERT: 67>
- Purpose: Boolean: monks can convert enemy units

- Defaults:

- 0: No

- 1: Yes (default)

### HIT_POINTS_KILLED        = <Attribute.HIT_POINTS_KILLED: 68>
- Purpose: Cumulative hp of all units killed

### FARM_FOOD_MULTIPLIER        = <Attribute.FARM_FOOD_MULTIPLIER: 69>
- Purpose: Multiplier for the amount of extra food granted by mill upgrades

- Defaults:

- 1: No multiplier (default)

### SOURCE_MARKET_OR_DOCK_X_COORDINATE        = <Attribute.SOURCE_MARKET_OR_DOCK_X_COORDINATE: 70>
- Purpose: Controls the amount of gold that trade carts and trade cogs deposit, when the source market is changed

### SOURCE_MARKET_OR_DOCK_Y_COORDINATE        = <Attribute.SOURCE_MARKET_OR_DOCK_Y_COORDINATE: 71>
- Purpose: Controls the amount of gold that trade carts and trade cogs deposit, when the source market is changed

### UNUSED_RESOURCE_72        = <Attribute.UNUSED_RESOURCE_72: 72>
- Purpose: Unused

### WAYPOINT_SPRITE_GRAPHIC_ID        = <Attribute.WAYPOINT_SPRITE_GRAPHIC_ID: 73>
- Purpose: Per-civ waypoint flag graphic ID

### UNUSED_RESOURCE_074        = <Attribute.UNUSED_RESOURCE_074: 74>
- Purpose: Unused

### UNUSED_RESOURCE_075        = <Attribute.UNUSED_RESOURCE_075: 75>
- Purpose: Unused

### UNUSED_RESOURCE_076        = <Attribute.UNUSED_RESOURCE_076: 76>
- Purpose: Unused

### CONVERSION_RESISTANCE        = <Attribute.CONVERSION_RESISTANCE: 77>
- Purpose: Coefficient of conversion resistance

- Defaults:

- 0: Default

- Note: Probability of conversion every monk second is divided by this value for ALL source player units.

### TRADE_VIG_RATE        = <Attribute.TRADE_VIG_RATE: 78>
- Purpose: Market exchange rate fraction for the source player

- Defaults:

- 0.3: Default

- 0.15: after Guilds

- 0.05: Saracens

### STONE_MINING_PRODUCTIVITY        = <Attribute.STONE_MINING_PRODUCTIVITY: 79>
- Purpose: Multiplier for stone mined by stone miners

- Defaults:

- 1: Default

- 1.15: Mayans

- Note: Since this works by multiplying the amount of resources gathered by a villager, it has a side effect of increasing the gather rate. In the case of Mayans, This is compensated for by reducing villager work rate by 15%

### QUEUED_UNITS        = <Attribute.QUEUED_UNITS: 80>
- Purpose: Amount of units in queue

- Note: Note that only the units waiting to be trained are considered in the queue so if an archery range has 3 archers being made, there is 1 archer that is being trained and 2 archers that are in queue

### TRAINING_COUNT        = <Attribute.TRAINING_COUNT: 81>
- Purpose: Amount of units being trained

- Note: Note that only the FIRST unit in each building is considered as being trained so if a town centre has 4 villagers being made, there is 1 archer that is being trained and 3 villagers that are in queue

### START_WITH_UNIT_444_PTWC        = <Attribute.START_WITH_UNIT_444_PTWC: 82>
- Purpose: Boolean: started with PTWC

- Note: Setting this to 1 in an RMS allows for starting with PTWC. Manually changing this in the editor does nothing

### UNUSED_RESOURCE_083        = <Attribute.UNUSED_RESOURCE_083: 83>
- Purpose: Unused

### STARTING_VILLAGERS        = <Attribute.STARTING_VILLAGERS: 84>
- Purpose: Number of starting villagers

- Defaults:

- 3: Default

- 4: Mayans

- 6: Chinese

- Note: Only works for RMS, changing this manually in the editor does nothing

### RESEARCH_COST_MODIFIER        = <Attribute.RESEARCH_COST_MODIFIER: 85>
- Purpose: Multiply technology costs by this value

- Defaults:

- 1: Default

- 0.9: Chinese in feudal age

- 0.85: Chinese in castle age

- 0.80: Chinese in imperial age

### RESEARCH_TIME_MODIFIER        = <Attribute.RESEARCH_TIME_MODIFIER: 86>
- Purpose: Multiply technology research times by this value

### CONVERT_BOATS        = <Attribute.CONVERT_BOATS: 87>
- Purpose: Boolean: allow monks to convert boats

- Defaults:

- 0: No

- 1: Yes (default)

### FISH_TRAP_FOOD_AMOUNT        = <Attribute.FISH_TRAP_FOOD_AMOUNT: 88>
- Purpose: Maximum fishtrap food amount

- Defaults:

- 710: Default

- 2130: Malay

### HEAL_RATE_MODIFIER        = <Attribute.HEAL_RATE_MODIFIER: 89>
- Purpose: Monk healing rate modifier

- Defaults:

- 0: The unit of measuremeant for this is unknown

### HEALING_RANGE        = <Attribute.HEALING_RANGE: 90>
- Purpose: Monk heal range

- Defaults:

- 4: Tiles

### STARTING_FOOD        = <Attribute.STARTING_FOOD: 91>
- Purpose: Starting food amount

- Note: Only works for RMS, changing this manually in the editor does nothing but its a way to check starting food amount

### STARTING_WOOD        = <Attribute.STARTING_WOOD: 92>
- Purpose: Starting wood amount

- Note: Only works for RMS, changing this manually in the editor does nothing but its a way to check starting wood amount

### STARTING_STONE        = <Attribute.STARTING_STONE: 93>
- Purpose: Starting stone amount

- Note: Only works for RMS, changing this manually in the editor does nothing but its a way to check starting stone amount

### STARTING_GOLD        = <Attribute.STARTING_GOLD: 94>
- Purpose: Starting gold amount

- Note: Only works for RMS, changing this manually in the editor does nothing but its a way to check starting gold amount

### ENABLE_PTWC_KIDNAP_LOOT        = <Attribute.ENABLE_PTWC_KIDNAP_LOOT: 95>
- Purpose: Enable town centre packing for the source player

- Defaults:

- 0: Default

- 1: Allows the TC to be packed and moved

- >=2: No noticeable effect

- Note: Enabling kidnap/loot requires modding the units to have the kidnap/pillage action

### NO_DROPSITE_FARMERS        = <Attribute.NO_DROPSITE_FARMERS: 96>
- Purpose: Enable Khmer farmer bonus

- Defaults:

- 0: Default

- 1: Khmer. Farmers no longer need dropoff and steadily gain resources while farming

### DOMINANT_SHEEP_CONTROL        = <Attribute.DOMINANT_SHEEP_CONTROL: 97>
- Purpose: Boolean: force sheep conversion

- Defaults:

- 0: Default

- >=1: Celts

- Note: If this is set to a non zero value, other players' sheep convert to you even if they have a unit in their LOS, unless this is also a non zero value for them. Celt sheep bonus

### BUILDING_COST_SUM        = <Attribute.BUILDING_COST_SUM: 98>
- Purpose: Total cost of all units and buildings owned

### TECH_COST_SUM        = <Attribute.TECH_COST_SUM: 99>
- Purpose: Total cost of all researches researched

### RELIC_INCOME_SUM        = <Attribute.RELIC_INCOME_SUM: 100>
- Purpose: Total relic gold generated

### TRADE_INCOME_SUM        = <Attribute.TRADE_INCOME_SUM: 101>
- Purpose: Total trade gold generated

### NAVAL_TRADE_WOOD        = <Attribute.NAVAL_TRADE_WOOD: 102>
- Purpose: Unknown

### UNUSED_RESOURCE_103        = <Attribute.UNUSED_RESOURCE_103: 103>
- Purpose: Unused

### UNUSED_RESOURCE_104        = <Attribute.UNUSED_RESOURCE_104: 104>
- Purpose: Unused

### UNUSED_RESOURCE_105        = <Attribute.UNUSED_RESOURCE_105: 105>
- Purpose: Unused

### UNUSED_RESOURCE_106        = <Attribute.UNUSED_RESOURCE_106: 106>
- Purpose: Unused

### UNUSED_RESOURCE_107        = <Attribute.UNUSED_RESOURCE_107: 107>
- Purpose: Unused

### UNUSED_RESOURCE_108        = <Attribute.UNUSED_RESOURCE_108: 108>
- Purpose: Unused

### UNUSED_RESOURCE_109        = <Attribute.UNUSED_RESOURCE_109: 109>
- Purpose: Unused

### UNUSED_RESOURCE_110        = <Attribute.UNUSED_RESOURCE_110: 110>
- Purpose: Unused

### UNUSED_RESOURCE_111        = <Attribute.UNUSED_RESOURCE_111: 111>
- Purpose: Unused

### UNUSED_RESOURCE_112        = <Attribute.UNUSED_RESOURCE_112: 112>
- Purpose: Unused

### UNUSED_RESOURCE_113        = <Attribute.UNUSED_RESOURCE_113: 113>
- Purpose: Unused

### UNUSED_RESOURCE_114        = <Attribute.UNUSED_RESOURCE_114: 114>
- Purpose: Unused

### UNUSED_RESOURCE_115        = <Attribute.UNUSED_RESOURCE_115: 115>
- Purpose: Unused

### UNUSED_RESOURCE_116        = <Attribute.UNUSED_RESOURCE_116: 116>
- Purpose: Unused

### UNUSED_RESOURCE_117        = <Attribute.UNUSED_RESOURCE_117: 117>
- Purpose: Unused

### UNUSED_RESOURCE_118        = <Attribute.UNUSED_RESOURCE_118: 118>
- Purpose: Unused

### UNUSED_RESOURCE_119        = <Attribute.UNUSED_RESOURCE_119: 119>
- Purpose: Unused

### UNUSED_RESOURCE_120        = <Attribute.UNUSED_RESOURCE_120: 120>
- Purpose: Unused

### UNUSED_RESOURCE_121        = <Attribute.UNUSED_RESOURCE_121: 121>
- Purpose: Unused

### UNUSED_RESOURCE_122        = <Attribute.UNUSED_RESOURCE_122: 122>
- Purpose: Unused

### UNUSED_RESOURCE_123        = <Attribute.UNUSED_RESOURCE_123: 123>
- Purpose: Unused

### UNUSED_RESOURCE_124        = <Attribute.UNUSED_RESOURCE_124: 124>
- Purpose: Unused

### UNUSED_RESOURCE_125        = <Attribute.UNUSED_RESOURCE_125: 125>
- Purpose: Unused

### UNUSED_RESOURCE_126        = <Attribute.UNUSED_RESOURCE_126: 126>
- Purpose: Unused

### UNUSED_RESOURCE_127        = <Attribute.UNUSED_RESOURCE_127: 127>
- Purpose: Unused

### UNUSED_RESOURCE_128        = <Attribute.UNUSED_RESOURCE_128: 128>
- Purpose: Unused

### UNUSED_RESOURCE_129        = <Attribute.UNUSED_RESOURCE_129: 129>
- Purpose: Unused

### UNUSED_RESOURCE_130        = <Attribute.UNUSED_RESOURCE_130: 130>
- Purpose: Unused

### UNUSED_RESOURCE_131        = <Attribute.UNUSED_RESOURCE_131: 131>
- Purpose: Unused

### UNUSED_RESOURCE_132        = <Attribute.UNUSED_RESOURCE_132: 132>
- Purpose: Unused

### UNUSED_RESOURCE_133        = <Attribute.UNUSED_RESOURCE_133: 133>
- Purpose: Unused

### STANDING_CASTLES        = <Attribute.STANDING_CASTLES: 134>
- Purpose: Number of standing castles

### HIT_POINTS_RAZED        = <Attribute.HIT_POINTS_RAZED: 135>
- Purpose: Total HP of all buildings destroyed

### UNUSED_RESOURCE_136        = <Attribute.UNUSED_RESOURCE_136: 136>
- Purpose: Unused

### UNUSED_RESOURCE_137        = <Attribute.UNUSED_RESOURCE_137: 137>
- Purpose: Unused

### UNUSED_RESOURCE_138        = <Attribute.UNUSED_RESOURCE_138: 138>
- Purpose: Unused

### UNUSED_RESOURCE_139        = <Attribute.UNUSED_RESOURCE_139: 139>
- Purpose: Unused

### UNUSED_RESOURCE_140        = <Attribute.UNUSED_RESOURCE_140: 140>
- Purpose: Unused

### UNUSED_RESOURCE_141        = <Attribute.UNUSED_RESOURCE_141: 141>
- Purpose: Unused

### UNUSED_RESOURCE_142        = <Attribute.UNUSED_RESOURCE_142: 142>
- Purpose: Unused

### UNUSED_RESOURCE_143        = <Attribute.UNUSED_RESOURCE_143: 143>
- Purpose: Unused

### UNUSED_RESOURCE_144        = <Attribute.UNUSED_RESOURCE_144: 144>
- Purpose: Unused

### UNUSED_RESOURCE_145        = <Attribute.UNUSED_RESOURCE_145: 145>
- Purpose: Unused

### UNUSED_RESOURCE_146        = <Attribute.UNUSED_RESOURCE_146: 146>
- Purpose: Unused

### UNUSED_RESOURCE_147        = <Attribute.UNUSED_RESOURCE_147: 147>
- Purpose: Unused

### UNUSED_RESOURCE_148        = <Attribute.UNUSED_RESOURCE_148: 148>
- Purpose: Unused

### UNUSED_RESOURCE_149        = <Attribute.UNUSED_RESOURCE_149: 149>
- Purpose: Unused

### UNUSED_RESOURCE_150        = <Attribute.UNUSED_RESOURCE_150: 150>
- Purpose: Unused

### UNUSED_RESOURCE_151        = <Attribute.UNUSED_RESOURCE_151: 151>
- Purpose: Unused

### VALUE_KILLED_BY_OTHERS        = <Attribute.VALUE_KILLED_BY_OTHERS: 152>
- Purpose: Total cost of all own units lost

### VALUE_RAZED_BY_OTHERS        = <Attribute.VALUE_RAZED_BY_OTHERS: 153>
- Purpose: Total cost of all own buildings lost

### KILLED_BY_OTHERS        = <Attribute.KILLED_BY_OTHERS: 154>
- Purpose: Number of own units killed by other players

### RAZED_BY_OTHERS        = <Attribute.RAZED_BY_OTHERS: 155>
- Purpose: Number of own buildings destroyed by other players

### UNUSED_RESOURCE_156        = <Attribute.UNUSED_RESOURCE_156: 156>
- Purpose: Unused

### UNUSED_RESOURCE_157        = <Attribute.UNUSED_RESOURCE_157: 157>
- Purpose: Unused

### UNUSED_RESOURCE_158        = <Attribute.UNUSED_RESOURCE_158: 158>
- Purpose: Unused

### UNUSED_RESOURCE_159        = <Attribute.UNUSED_RESOURCE_159: 159>
- Purpose: Unused

### UNUSED_RESOURCE_160        = <Attribute.UNUSED_RESOURCE_160: 160>
- Purpose: Unused

### UNUSED_RESOURCE_161        = <Attribute.UNUSED_RESOURCE_161: 161>
- Purpose: Unused

### UNUSED_RESOURCE_162        = <Attribute.UNUSED_RESOURCE_162: 162>
- Purpose: Unused

### UNUSED_RESOURCE_163        = <Attribute.UNUSED_RESOURCE_163: 163>
- Purpose: Unused

### VALUE_CURRENT_UNITS        = <Attribute.VALUE_CURRENT_UNITS: 164>
- Purpose: Total cost of all own alive units

### VALUE_CURRENT_BUILDINGS        = <Attribute.VALUE_CURRENT_BUILDINGS: 165>
- Purpose: Total cost of all own standing buildings

### FOOD_TOTAL        = <Attribute.FOOD_TOTAL: 166>
- Purpose: Total food collected

### WOOD_TOTAL        = <Attribute.WOOD_TOTAL: 167>
- Purpose: Total wood collected

### STONE_TOTAL        = <Attribute.STONE_TOTAL: 168>
- Purpose: Total stone collected

### GOLD_TOTAL        = <Attribute.GOLD_TOTAL: 169>
- Purpose: Total gold collected

### TOTAL_VALUE_OF_KILLS        = <Attribute.TOTAL_VALUE_OF_KILLS: 170>
- Purpose: Total cost of all units killed

### TOTAL_TRIBUTE_RECEIVED        = <Attribute.TOTAL_TRIBUTE_RECEIVED: 171>
- Purpose: Total of all resources received in tribute

### TOTAL_VALUE_OF_RAZINGS        = <Attribute.TOTAL_VALUE_OF_RAZINGS: 172>
- Purpose: Total cost of all buildings destroyed

### TOTAL_CASTLES_BUILT        = <Attribute.TOTAL_CASTLES_BUILT: 173>
- Purpose: Number of total castles built

### TOTAL_WONDERS_BUILT        = <Attribute.TOTAL_WONDERS_BUILT: 174>
- Purpose: Number of total wonders built

### TRIBUTE_SCORE        = <Attribute.TRIBUTE_SCORE: 175>
- Purpose: Total amount of resources sent in tribute including taxes. 10% of this is counted towards the economy score

### CONVERT_MIN_ADJUSTMENT        = <Attribute.CONVERT_MIN_ADJUSTMENT: 176>
- Purpose: Additional monk seconds needed before a conversion is even possible

- Note: A great explanation of how this works: https://youtu.be/-qRUaOHpbwI?t=870 by T-West

### CONVERT_MAX_ADJUSTMENT        = <Attribute.CONVERT_MAX_ADJUSTMENT: 177>
- Purpose: Additional monk seconds needed before a conversion is forced

- Note: A great explanation of how this works: https://youtu.be/-qRUaOHpbwI?t=870 by T-West

### CONVERT_RESIST_MIN_ADJUSTMENT        = <Attribute.CONVERT_RESIST_MIN_ADJUSTMENT: 178>
- Purpose: Additional monk seconds needed before conversion by enemy monks is even possible

- Note: A great explanation of how this works: https://youtu.be/-qRUaOHpbwI?t=830 by T-West

### CONVERT_RESIST_MAX_ADJUSTMENT        = <Attribute.CONVERT_RESIST_MAX_ADJUSTMENT: 179>
- Purpose: Additional monk seconds needed before conversion by enemy monks is forced

- Note: A great explanation of how this works: https://youtu.be/-qRUaOHpbwI?t=830 by T-West.

### CONVERT_BUILDING_MIN        = <Attribute.CONVERT_BUILDING_MIN: 180>
- Purpose: Minimum time required to convert a building

- Note: A great explanation of how this works: https://youtu.be/-qRUaOHpbwI?t=902 by T-West

### CONVERT_BUILDING_MAX        = <Attribute.CONVERT_BUILDING_MAX: 181>
- Purpose: Maximum time required to convert a building

- Note: A great explanation for how this works: https://youtu.be/-qRUaOHpbwI?t=902 by T-West

### CONVERT_BUILDING_CHANCE        = <Attribute.CONVERT_BUILDING_CHANCE: 182>
- Purpose: Percent chance for monks to convert buildings

- Note: A great explanation for how this works: https://youtu.be/-qRUaOHpbwI?t=902 by T-West

### REVEAL_ENEMY        = <Attribute.REVEAL_ENEMY: 183>
- Purpose: Boolean: show enemy los for the source player

- Defaults:

- 0: No (default)

- 1: Yes, after Spies

- Note: Once set to 1, setting it back to 0 won't take away LoS of enemies!

### VALUE_WONDERS_CASTLES        = <Attribute.VALUE_WONDERS_CASTLES: 184>
- Purpose: Total cost of all wonders and castles constructed

### FOOD_SCORE        = <Attribute.FOOD_SCORE: 185>
- Purpose: Unknown... what does this resource do?

### WOOD_SCORE        = <Attribute.WOOD_SCORE: 186>
- Purpose: Unknown... what does this resource do?

### STONE_SCORE        = <Attribute.STONE_SCORE: 187>
- Purpose: Unknown... what does this resource do?

### GOLD_SCORE        = <Attribute.GOLD_SCORE: 188>
- Purpose: Unknown... what does this resource do?

### CHOPPING_PRODUCTIVITY        = <Attribute.CHOPPING_PRODUCTIVITY: 189>
- Purpose: Multiplier for wood chopped by lumberjacks

- Defaults:

- 1: Default

- 1.15: Mayans

- Note: Since this works by multiplying the amount of resources gathered by a villager, it has a side effect of increasing the gather rate. In the case of Mayans, This is compensated for by reducing villager work rate by 15%

### FOOD_GATHERING_PRODUCTIVITY        = <Attribute.FOOD_GATHERING_PRODUCTIVITY: 190>
- Purpose: Multiplier for food gathered from all sources

- Defaults:

- 1: Default

- 1.15: Mayans

- Note: Since this works by multiplying the amount of resources gathered by a villager, it has a side effect of increasing the gather rate. In the case of Mayans, This is compensated for by reducing villager work rate by 15%. The work rate for farmers is reduced by about 23.4%

### RELIC_GOLD_PRODUCTION_RATE        = <Attribute.RELIC_GOLD_PRODUCTION_RATE: 191>
- Purpose: Relic gold generation rate in gold per minute

- Defaults:

- 30: Default. 30 gold per minute (0.5 gold per second)

- 15: After getting hit with Atheism

### CONVERTED_UNITS_DIE        = <Attribute.CONVERTED_UNITS_DIE: 192>
- Purpose: Boolean: converted units die instead of switching over to the enemy

- Defaults:

- 0: No (default)

- 1: Yes, after Heresey

### THEOCRACY        = <Attribute.THEOCRACY: 193>
- Purpose: Boolean: only one monk needs to regen faith after group conversion for the source player

- Defaults:

- 0: No (default)

- 1: Yes, after researching Theocracy

### UNUSED_RESOURCE_194        = <Attribute.UNUSED_RESOURCE_194: 194>
- Purpose: Unused

### CONSTRUCTION_RATE_MODIFIER        = <Attribute.CONSTRUCTION_RATE_MODIFIER: 195>
- Purpose: Builder work rate multiplier

- Defaults:

- 0: Default

- 1.3: Spanish

- Note: The actual work rate for builders is given by construction_rate_mod * builder.default_work_rate

### WONDER_TIME_MODIFIER        = <Attribute.WONDER_TIME_MODIFIER: 196>
- Purpose: Additional time required for wonder victories in one tenth of a year

- Defaults:

- 0: default

- 1000: (100 years) for all neutral/enemies of the Hun player, after researching atheism. The value of this resource of each player is added to determine the total extra time for wonder victories, i.e. it adds up if multiple hun players get the tech

- Note: Internally, wonder victory countdowns are measured in one tenths of an year, the fractional part is just not shown ingame

### SPIES_DISCOUNT        = <Attribute.SPIES_DISCOUNT: 197>
- Purpose: Boolean: Halves the cost of spies per villager, and caps it at 15k gold max instead of the usual 30k

- Defaults:

- 0: Default

### RELIC_TIME_MODIFIER        = <Attribute.RELIC_TIME_MODIFIER: 198>
- Purpose: Additional time required for relic victories in one tenth of a year

- Defaults:

- 0: default

- 1000: (100 years) for all neutral/enemies of the Hun player, after researching atheism. The value of this resource of each player is added to determine the total extra time for relic victories, i.e. it adds up if multiple hun players get the tech

- Note: Internally, wonder victory countdowns are measured in one tenths of an year, the fractional part is just not shown ingame

### UNUSED_RESOURCE_199        = <Attribute.UNUSED_RESOURCE_199: 199>
- Purpose: Unused

### UNUSED_RESOURCE_200        = <Attribute.UNUSED_RESOURCE_200: 200>
- Purpose: Unused

### UNUSED_RESOURCE_201        = <Attribute.UNUSED_RESOURCE_201: 201>
- Purpose: Unused

### UNUSED_RESOURCE_202        = <Attribute.UNUSED_RESOURCE_202: 202>
- Purpose: Unused

### MAP_REVEAL        = <Attribute.MAP_REVEAL: 203>
- Purpose: Controls the map visibility for a player.

- Defaults:

- 0: Normal

- 1: Explored

- 2: All Visible

### UNIT_REVEAL        = <Attribute.UNIT_REVEAL: 204>
- Purpose: Controls the visibility of other players' units for a player

- Note: Positive IDs will reveal a unit temporarily only when it is created, Negative IDs will reveal a unit permanently

### FEITORIA_FOOD_PRODUCTIVITY        = <Attribute.FEITORIA_FOOD_PRODUCTIVITY: 205>
- Purpose: Feitoria food production rate multiplier

- Defaults:

- 1: Default

- Note: The amount of food obtained from owning n number of Feitorias is given by n * feitoria_food_productivity * 1.6

### FEITORIA_WOOD_PRODUCTIVITY        = <Attribute.FEITORIA_WOOD_PRODUCTIVITY: 206>
- Purpose: Feitoria wood production rate multiplier

- Defaults:

- 1: Default

- Note: The amount of wood obtained from owning n number of Feitorias is given by n * feitoria_wood_productivity * 0.7

### FEITORIA_STONE_PRODUCTIVITY        = <Attribute.FEITORIA_STONE_PRODUCTIVITY: 207>
- Purpose: Feitoria stone production rate multiplier

- Defaults:

- 1: Default

- Note: The amount of stone obtained from owning n number of Feitorias is given by n * feitoria_stone_productivity * 0.3

### FEITORIA_GOLD_PRODUCTIVITY        = <Attribute.FEITORIA_GOLD_PRODUCTIVITY: 208>
- Purpose: Feitoria gold production rate multiplier

- Defaults:

- 1: Default

- Note: The amount of gold obtained from owning n number of Feitorias is given by n * feitoria_gold_productivity * 1

### REVEAL_ENEMY_TOWN_CENTERS        = <Attribute.REVEAL_ENEMY_TOWN_CENTERS: 209>
- Purpose: Boolean: reveal enemy town centre location for the source player

- Defaults:

- 0: Default

- 5: Vietnamese

- Note: The bonus works for all values >=1, the choice of setting it to 5 for vietnamese seems arbitrary

### RELICS_VISIBLE_ON_MAP        = <Attribute.RELICS_VISIBLE_ON_MAP: 210>
- Purpose: Boolean: reveal relics on map amount

- Defaults:

- -1: Default

- 42: Burmese

- Note: Burmese reveal relics on map bonus. Only works in RMS, manually changing this in the editor does not seem to have any effects

### ELEVATION_HIGHER_BONUS        = <Attribute.ELEVATION_HIGHER_BONUS: 211>
- Purpose: The fraction for additional bonus damage dealt from higher elevation

- Defaults:

- 0: Default

- 0.25: Tatars

- Note: Damage that units on higher elevation deal to units on lower elevation is multiplied by 1.25 + elevation_bonus_higher

### ELEVATION_LOWER_BONUS        = <Attribute.ELEVATION_LOWER_BONUS: 212>
- Purpose: The fraction for additional bonus damage dealt from lower elevation

- Defaults:

- 0: Default

- Note: Damage that units on lower elevation deal to units on higher elevation is multiplied by 0.75 + elevation_bonus_lower

### RAIDING_PRODUCTIVITY        = <Attribute.RAIDING_PRODUCTIVITY: 213>
- Purpose: Keshik gold generation rate per 100 seconds

- Defaults:

- 0: Default

- 50: (0.5 g/s) Tatars

- Note: Note that in practice, due to attack reload time and frame delay, Keshiks don't actually produce 0.5 g/s, but a slightly lower value

### MERCENARY_KIPCHAK_COUNT        = <Attribute.MERCENARY_KIPCHAK_COUNT: 214>
- Purpose: Total number of mercenary kipchak creatable

- Note: Researching Cuman Mercenaries gives 5 of this resource per castle. Making mercenary Kipchaks costs one unit of this resource. Each newly constructed castle gives +5

### BONUS_FORAGER_FOOD        = <Attribute.BONUS_FORAGER_FOOD: 215>
- Purpose: Bonus forager food gathering percent of main work rate

- Defaults:

- 0: Default

- 25: Mapuche

- Note: EffectFunction29 must be called in order for this resource to work

### SHEPHERD_PRODUCTIVITY        = <Attribute.SHEPHERD_PRODUCTIVITY: 216>
- Purpose: Amount of food collected from sheep multiplier

- Defaults:

- 1: Default

- 1.57: Tatars

- Note: Since this works by multiplying the amount of resources gathered by a villager, it has a side effect of increasing the gather rate. In the case of Tatars, This is compensated for by reducing villager work rate by 57%

### SHARED_LINE_OF_SIGHT        = <Attribute.SHARED_LINE_OF_SIGHT: 217>
- Purpose: Unused

### EARLY_TOWN_CENTER_LIMIT        = <Attribute.EARLY_TOWN_CENTER_LIMIT: 218>
- Purpose: This is the number of extra TCs a player is allowed to build IF TCs are enabled in feudal age

- Defaults:

- 1: Default

- 2: Cumans

- Note: Since generic civs don't get access to TCs in feudal, the 10k amount doesn't matter, but if you're trying to make a map where you want people to be able to make TCs in feudal, make sure to set this value to 10k for cumans!

### FISHING_PRODUCTIVITY        = <Attribute.FISHING_PRODUCTIVITY: 219>
- Purpose: Multiplier for food gathered by fishing ships

- Defaults:

- 1: Default

- Note: Since this works by multiplying the amount of resources gathered by a fishing ship, it has a side effect of increasing the gather rate

### ENABLE_CERTAIN_HERO_LEVEL_UP_UNUSED_RESOURCE_220        = <Attribute.ENABLE_CERTAIN_HERO_LEVEL_UP_UNUSED_RESOURCE_220: 220>
- Purpose: Enables leveling up when killing units for Richard the Lionheart, Sieur de Metz, Kushluk, Zawisza the Black

- Defaults:

- 0: Default

- Note: - This enabled Loot task which makes these heroes gain stats instead of resources.

- The editor name of the resource is incorrect

### MONUMENT_FOOD_PRODUCTIVITY        = <Attribute.MONUMENT_FOOD_PRODUCTIVITY: 221>
- Purpose: Monument food trickle rate multiplier

- Defaults:

- 1: In KoTH games

- Note: The amount of resources obtained by owning a monument is 0.7925 * food_trickle_from_monument

### MONUMENT_WOOD_PRODUCTIVITY        = <Attribute.MONUMENT_WOOD_PRODUCTIVITY: 222>
- Purpose: Monument wood trickle rate multiplier

- Defaults:

- 1: In KoTH games

- Note: The amount of resources obtained by owning a monument is 0.7925 * wood_trickle_from_monument

### MONUMENT_STONE_PRODUCTIVITY        = <Attribute.MONUMENT_STONE_PRODUCTIVITY: 223>
- Purpose: Monument stone trickle rate multiplier

- Defaults:

- 1: In KoTH games

- Note: The amount of resources obtained by owning a monument is 0.7925 * stone_trickle_from_monument

### MONUMENT_GOLD_PRODUCTIVITY        = <Attribute.MONUMENT_GOLD_PRODUCTIVITY: 224>
- Purpose: Monument gold trickle rate multiplier

- Defaults:

- 1: In KoTH games

- Note: The amount of resources obtained by owning a monument is 0.7925 * gold_trickle_from_monument

### RELIC_FOOD_PRODUCTION_RATE        = <Attribute.RELIC_FOOD_PRODUCTION_RATE: 225>
- Purpose: Relic food production per minute

- Defaults:

- 0: Default

- 30: Burgundians

- 15: Burgundians after getting hit with Atheism

### VILLAGERS_KILLED_BY_GAIA        = <Attribute.VILLAGERS_KILLED_BY_GAIA: 226>
- Purpose: Total number of villagers lost to gaia

### VILLAGERS_KILLED_BY_ANIMALS        = <Attribute.VILLAGERS_KILLED_BY_ANIMALS: 227>
- Purpose: Total number of villagers lost to wild animals

### VILLAGERS_KILLED_BY_AI_PLAYER        = <Attribute.VILLAGERS_KILLED_BY_AI_PLAYER: 228>
- Purpose: Total number of villagers lost to AIs

### VILLAGERS_KILLED_BY_HUMAN_PLAYER        = <Attribute.VILLAGERS_KILLED_BY_HUMAN_PLAYER: 229>
- Purpose: Total number of villagers lost to human players

### FOOD_GENERATION_RATE        = <Attribute.FOOD_GENERATION_RATE: 230>
- Purpose: Free food trickle rate (per minute)

### WOOD_GENERATION_RATE        = <Attribute.WOOD_GENERATION_RATE: 231>
- Purpose: Free wood trickle rate (per minute)

### STONE_GENERATION_RATE        = <Attribute.STONE_GENERATION_RATE: 232>
- Purpose: Free stone trickle rate (per minute)

### GOLD_GENERATION_RATE        = <Attribute.GOLD_GENERATION_RATE: 233>
- Purpose: Free gold trickle rate (per minute)

### SPAWN_LIMIT        = <Attribute.SPAWN_LIMIT: 234>
- Purpose: The limit to the number of spawning buildings that can spawn units from spawn command in a technology

- Note: This is usually overridden by techs

### FLEMISH_MILITIA_POPULATION        = <Attribute.FLEMISH_MILITIA_POPULATION: 235>
- Purpose: Number of alive flemish militia

### FARMING_GOLD_PRODUCTIVITY        = <Attribute.FARMING_GOLD_PRODUCTIVITY: 236>
- Purpose: Farmer gold generation percent of main work rate

- Defaults:

- 0: Default

- 2: Burgundian Vineyards

- Note: EffectFunction14 must be called for this resource to work. Only generates gold while collecting food from farms, and not when walking on them down

### FOLWARK_COLLECTION_AMOUNT        = <Attribute.FOLWARK_COLLECTION_AMOUNT: 237>
- Purpose: This is the amount of food collected from farms built around a folwark

- Defaults:

- 0: Default

- 17.5: Poles

- 19.25: Poles with Chinese Ally

- 25: Poles with Horse Collar

- 27.5: Poles with Horse Collar & Chinese Ally

- 37.5: Poles with Heavy Plow

- 41.25: Poles with Heavy Plow & Chinese Ally

- 55: Poles with Crop Rotation

- 60.5: Poles with Crop Rotation & Chinese Ally

### FOLWARK_ATTRIBUTE_TYPE        = <Attribute.FOLWARK_ATTRIBUTE_TYPE: 238>
- Purpose: This is the ID of the resource that is given when a farm is constructed around a folwark

- Defaults:

- 0: Poles

- -1: Default

### FOLWARK_BUILDING_TYPE        = <Attribute.FOLWARK_BUILDING_TYPE: 239>
- Purpose: This is the ID of the building that the Folwark needs to upgrade from for the farm collection ability to work

- Defaults:

- 68: (Mill) Poles

- -1: Default

### UNITS_CONVERTED        = <Attribute.UNITS_CONVERTED: 240>
- Purpose: The amount of units lost to enemy conversions

### STONE_MINING_GOLD_PRODUCTIVITY        = <Attribute.STONE_MINING_GOLD_PRODUCTIVITY: 241>
- Purpose: Bonus stone miner gold gathering percent of main work rate

- Defaults:

- 0: Default

- 33.33: Poles

- Note: EffectFunction13 must be called for this resource to work

### TRADE_WORKSHOP_FOOD_PRODUCTIVITY        = <Attribute.TRADE_WORKSHOP_FOOD_PRODUCTIVITY: 242>
- Purpose: Trade Workshop food production rate multiplier

- Defaults:

- 1: Default

- Note: The amount of food obtained from owning n number of TWS (Unit 1647) is given by n * tws_food_productivity * 2.25

### TRADE_WORKSHOP_WOOD_PRODUCTIVITY        = <Attribute.TRADE_WORKSHOP_WOOD_PRODUCTIVITY: 243>
- Purpose: Trade Workshop wood production rate multiplier

- Defaults:

- 1: Default

- Note: The amount of wood obtained from owning n number of TWS (Unit 1647) is given by n * tws_wood_productivity * 2.25

### TRADE_WORKSHOP_STONE_PRODUCTIVITY        = <Attribute.TRADE_WORKSHOP_STONE_PRODUCTIVITY: 244>
- Purpose: Trade Workshop stone production rate multiplier

- Defaults:

- 0: Default

- Note: The amount of stone obtained from owning n number of TWS (Unit 1647) is given by n * tws_stone_productivity * 2.25

### TRADE_WORKSHOP_GOLD_PRODUCTIVITY        = <Attribute.TRADE_WORKSHOP_GOLD_PRODUCTIVITY: 245>
- Purpose: Trade Workshop gold production rate multiplier

- Defaults:

- 1: Default

- Note: The amount of gold obtained from owning n number of TWS (Unit 1647) is given by n * tws_gold_productivity * 2.25

### UNITS_VALUE_TOTAL        = <Attribute.UNITS_VALUE_TOTAL: 246>
- Purpose: Total cost of all units created so far

- Note: This does not decrease when the units die

### BUILDINGS_VALUE_TOTAL        = <Attribute.BUILDINGS_VALUE_TOTAL: 247>
- Purpose: Total cost of all buildings created so far

- Note: Increases when foundations are placed. This does not decrease if the foundation is deleted

### VILLAGERS_CREATED_TOTAL        = <Attribute.VILLAGERS_CREATED_TOTAL: 248>
- Purpose: Total number of villagers created so far

### VILLAGERS_IDLE_PERIODS_TOTAL        = <Attribute.VILLAGERS_IDLE_PERIODS_TOTAL: 249>
- Purpose: Amount of villagers that entered an idle state since game start

- Note:

- This only updates every 5 physical minutes.

- The number of villagers that entered an idle state since the last updated is added to this resource.

- Starting villager count is the initial value

### VILLAGERS_IDLE_SECONDS_TOTAL        = <Attribute.VILLAGERS_IDLE_SECONDS_TOTAL: 250>
- Purpose: Amount of total seconds all villagers have been idle since game start

- Note:

- This only updates every 5 physical minutes.

- The idle time in seconds for all villagers since the last time this resource was updated is added  to this resource.

- A villager immediately adds its own idle time to this resource if it dies

### TRADE_FOOD_PERCENT        = <Attribute.TRADE_FOOD_PERCENT: 251>
- Purpose: Percentage of gold generated from trade that is also given as food

- Defaults:

- 0: Default

- 10: Bengalis

### TRADE_WOOD_PERCENT        = <Attribute.TRADE_WOOD_PERCENT: 252>
- Purpose: Percentage of gold generated from trade that is also given as wood

- Defaults:

- 0: Default

### TRADE_STONE_PERCENT        = <Attribute.TRADE_STONE_PERCENT: 253>
- Purpose: Percentage of gold generated from trade that is also given as stone

- Defaults:

- 0: Default

### LIVESTOCK_FOOD_PRODUCTIVITY        = <Attribute.LIVESTOCK_FOOD_PRODUCTIVITY: 254>
- Purpose: Garrisoned herdable food generation rate per 60 seconds

- Defaults:

- 0: Default

- 3.5: (0.0583 f/s per herdable) Gurjaras

### UNUSED_RESOURCE_255        = <Attribute.UNUSED_RESOURCE_255: 255>
- Purpose: Unused

### UNUSED_RESOURCE_256        = <Attribute.UNUSED_RESOURCE_256: 256>
- Purpose: Unused

### UNUSED_RESOURCE_257        = <Attribute.UNUSED_RESOURCE_257: 257>
- Purpose: Unused

### UNUSED_RESOURCE_258        = <Attribute.UNUSED_RESOURCE_258: 258>
- Purpose: Unused

### UNUSED_RESOURCE_259        = <Attribute.UNUSED_RESOURCE_259: 259>
- Purpose: Unused

### UNUSED_RESOURCE_260        = <Attribute.UNUSED_RESOURCE_260: 260>
- Purpose: Unused

### UNUSED_RESOURCE_261        = <Attribute.UNUSED_RESOURCE_261: 261>
- Purpose: Unused

### CIVILIZATION_NAME_OVERRIDE        = <Attribute.CIVILIZATION_NAME_OVERRIDE: 262>
- Purpose:

### STARTING_SCOUT_ID        = <Attribute.STARTING_SCOUT_ID: 263>
- Purpose: Unit ID for the starting scout. Can be set to any unit (even buildings)

- Defaults:

- 448: (Scout Cavalry) Default

- 751: (Eagle Scout) Aztecs, Incas and Mayans

- 1755: (Camel Scout) Gurjaras

### RELIC_WOOD_PRODUCTION_RATE        = <Attribute.RELIC_WOOD_PRODUCTION_RATE: 264>
- Purpose: Relic wood production per minute

- Defaults:

- 0: Default

- Note: This is not affected by Atheism

### RELIC_STONE_PRODUCTION_RATE        = <Attribute.RELIC_STONE_PRODUCTION_RATE: 265>
- Purpose: Relic stone production per minute

- Note: This is not affected by Atheism

### CHOPPING_GOLD_PRODUCTIVITY        = <Attribute.CHOPPING_GOLD_PRODUCTIVITY: 266>
- Purpose: Lumberjack chopping gold gathering percent of main work rate

- Defaults:

- 0: Default

- 1.5: Paper Money

- Note: EffectFunction15 must be called for this resource to work. Only generates gold while collecting wood from trees, and not when cutting them down

### FORAGING_WOOD_PRODUCTIVITY        = <Attribute.FORAGING_WOOD_PRODUCTIVITY: 267>
- Purpose: Bonus forager wood gathering percent of main work rate

- Defaults:

- 0: Default

- 33.33: Portuguese

- Note: EffectFunction12 must be called for this resource to work

### HUNTER_PRODUCTIVITY        = <Attribute.HUNTER_PRODUCTIVITY: 268>
- Purpose: Hunter hunting gold production rate per 100 seconds

### TECHNOLOGY_REWARD_EFFECT        = <Attribute.TECHNOLOGY_REWARD_EFFECT: 269>
- Purpose: This is the ID of an additional effect which will fire when any technology is researched

### UNIT_REPAIR_COST        = <Attribute.UNIT_REPAIR_COST: 270>
- Purpose: Percentage of cost required to repair siege units and ships

### BUILDING_REPAIR_COST        = <Attribute.BUILDING_REPAIR_COST: 271>
- Purpose: Percentage of cost required to repair buildings

### ELEVATION_HIGHER_DAMAGE        = <Attribute.ELEVATION_HIGHER_DAMAGE: 272>
- Purpose: Damage modifier for own units when attacked from higher elevation

- Note: This is applied after the calculations from Elevation Higher Bonus and Elevation Lower Bonus

### ELEVATION_LOWER_DAMAGE        = <Attribute.ELEVATION_LOWER_DAMAGE: 273>
- Purpose: Damage modifier for own units when attacked from lower elevation

- Note: This is applied after the calculations from Elevation Higher Bonus and Elevation Lower Bonus

### INFANTRY_KILL_REWARD        = <Attribute.INFANTRY_KILL_REWARD: 274>
- Purpose: This resource currently effectively enables/disables gold generation per second by infantry killing villagers, trade units and monks

- Defaults:

- 0: All Civs

- 1: Vikings after Chieftains

- Note: Technically, this resource is used as a multiplier for the resource generated by task 154 currently on infantry units. Task 154 can change which resource does this, and it is what really controls which resource is generated (Resource Out) and the rate of generation (Work Value 1) which is set to the different rates for different types of targets for infantry

### FYRD_DISCOUNT_LEVEL        = <Attribute.FYRD_DISCOUNT_LEVEL: 275>
- Purpose: The number of standing castles + TCs

- Note: This value only changes when a player is playing as the Saxons.

### BONUS_GOLD_PRODUCTIVITY        = <Attribute.BONUS_GOLD_PRODUCTIVITY: 276>
- Purpose: Bonus gold miner gold gathering percent of main work rate

- Defaults:

- 0: Default

- 10: Malians

- Note: EffectFunction11 must be called in order for this resource to work

### RED_CLIFFS_TACTICS_DAMAGE        = <Attribute.RED_CLIFFS_TACTICS_DAMAGE: 277>
- Purpose: Multiplier for the amount of fire damage done by demolition ships

- Defaults:

- 0: Before red cliffs tactics is researched

- 1: After red cliffs tactics is researched

- Note: This implies that converted units that are affected by the tech won't do fire damage after being converted

### RAZING_BOUNTY        = <Attribute.RAZING_BOUNTY: 278>
- Purpose: Currently Unused

### MILITARY_CAN_CONVERT        = <Attribute.MILITARY_CAN_CONVERT: 279>
- Purpose: Military units with the conversion task can convert units if this is set to > 0 for a player

### MILITARY_CONVERT_RANGE        = <Attribute.MILITARY_CONVERT_RANGE: 280>
- Purpose: Adds to the conversion range of military units

### MILITARY_CONVERT_CHANCE        = <Attribute.MILITARY_CONVERT_CHANCE: 281>
- Purpose: Determines the conversion probability per monk second

### MILITARY_CONVERT_RECHARGE        = <Attribute.MILITARY_CONVERT_RECHARGE: 282>
- Purpose: Determines the faith recharge rate after successful conversions

### SPAWN_INSIDE        = <Attribute.SPAWN_INSIDE: 283>
- Purpose: Determines whenever spawned unit via xsEffectAmount(cSpawnUnit,...) or certain techs is spawned garrisoned or outside

- Defaults:

- 0: All Civs

- 1: Set briefly for the Armenians after their first Fortified Church is built to spawn the relic garrisoned.

- Note: This is usually overridden by techs

### CAVALRY_KILL_REWARD        = <Attribute.CAVALRY_KILL_REWARD: 284>
- Purpose: This resource effectively sets the gold generation rate per second by cavalry fighting other military units

- Defaults:

- 0: All Civs

- Note: Technically, this resource is used as a multiplier for the resource generated by task 154 currently on cavalry units. Task 154 can change which resource does this, and it is also what really controls which resource is generated (Resource Out) and the rate of generation (Work Value 1) which is just set to 1 for cavalry.

### SHARED_VISIBILITY        = <Attribute.SHARED_VISIBILITY: 285>
- Purpose: This is a bitfield where the lowest 9 bits toggle sharing LoS with a specific player. The lowest bit represents gaia (player 0), and each higher bit represents the next player, so the bit for a given player is 1 << player (pow(2, player)).

- Note: This does not change LoS for allies if the shared exploration setting in the lobby is enabled. Since this resource is a bitfield, when reading it with xsPlayerAttribute or setting it with xsSetPlayerAttribute, the value requires to be converted using bitCastToInt and bitCastToFloat respectively, so that the individual bits can be read and set correctly.

### SHARED_EXPLORATION        = <Attribute.SHARED_EXPLORATION: 286>
- Purpose: This is a bitfield where the lowest 9 bits toggle sharing map exploration with a specific player. The lowest bit represents gaia (player 0), and each higher bit represents the next player, so the bit for a given player is 1 << player (pow(2, player)).

- Note: This does not change exploration for allies if the shared exploration setting in the lobby is enabled. Since this resource is a bitfield, when reading it with xsPlayerAttribute or setting it with xsSetPlayerAttribute, the value requires to be converted using bitCastToInt and bitCastToFloat respectively, so that the individual bits can be read and set correctly.

### MILITARY_FOOD_PRODUCTIVITY        = <Attribute.MILITARY_FOOD_PRODUCTIVITY: 287>
- Purpose: The amount of food generated by soldiers per 100 seconds

### PASTURE_FOOD_AMOUNT        = <Attribute.PASTURE_FOOD_AMOUNT: 288>
- Purpose: Determines the amount of food pastures provide

### PASTURE_ANIMAL_COUNT        = <Attribute.PASTURE_ANIMAL_COUNT: 289>
- Purpose: Determines the amount of animals on a pasture.

### PASTURE_HERDER_COUNT        = <Attribute.PASTURE_HERDER_COUNT: 290>
- Purpose: Determines the maximum amount of villagers that can work at once on a pasture

### RAZING_PILLAGE        = <Attribute.RAZING_PILLAGE: 291>
- Purpose: The percent * 10 of the cost that should be looted when destroying buildings.

- Defaults:

- 0: Default

- 250: Danes

- Note: EffectFunction36 must be called for all players in the game for this resource to work.

### ANIMAL_DECAY_PREVENTION        = <Attribute.ANIMAL_DECAY_PREVENTION: 292>
- Purpose: Prevents animal corpses from losing food when being gathered by a villager

### HERDER_FOOD_PRODUCTIVITY        = <Attribute.HERDER_FOOD_PRODUCTIVITY: 293>
- Purpose: Percent extra food generated by herders and shepherds

### SHEPHERD_FOOD_PRODUCTIVITY        = <Attribute.SHEPHERD_FOOD_PRODUCTIVITY: 294>
- Purpose: Percent extra food generated by herders and shepherds

### UNIT_REFUND        = <Attribute.UNIT_REFUND: 295>
- Purpose: Fraction of the cost to refund for lost units for the player

- Defaults:

- 0: Default

- 0.15: Tupi

- Note: EffectFunction27 must be called for this resource to work.

### FORAGER_PRODUCTIVITY        = <Attribute.FORAGER_PRODUCTIVITY: 296>
- Purpose: Multiplier for food collected by foragers

- Defaults:

- 1: Default

### VARANGIAN_GOLD_GENERATION        = <Attribute.VARANGIAN_GOLD_GENERATION: 297>
- Purpose: Varangian Guard gold generation multiplier

- Defaults:

- 1: Default

- 1.33: Varangians

### BUTCHER_GOLD_PRODUCTIVITY        = <Attribute.BUTCHER_GOLD_PRODUCTIVITY: 298>
- Purpose: Varangians Shepherd/Hunter/Fisher/Fishing Ship additional gold gathering percent of main work rate

- Defaults:

- 0: Default

- 10.01: Varangians

- Note: EffectFunction34 must be called for this resource to work.

### BONUS_FOOD_PRODUCTIVITY        = <Attribute.BONUS_FOOD_PRODUCTIVITY: 299>
- Purpose: All food gatherers additional food gathering percent of main work rate

- Defaults:

- 0: Default

- 5.01: Danes

- Note: EffectFunction35 must be called for this resource to work.

### KILLED_GAIA        = <Attribute.KILLED_GAIA: 300>
- Purpose: Number of gaia units killed

### KILLED_P1        = <Attribute.KILLED_P1: 301>
- Purpose: Number of player1 units killed

- Note: This refers to lobby/slot/world player 1, not editor/scenario player 1

### KILLED_P2        = <Attribute.KILLED_P2: 302>
- Purpose: Number of player2 units killed

- Note: This refers to lobby/slot/world player 2, not editor/scenario player 2

### KILLED_P3        = <Attribute.KILLED_P3: 303>
- Purpose: Number of player3 units killed

- Note: This refers to lobby/slot/world player 3, not editor/scenario player 3

### KILLED_P4        = <Attribute.KILLED_P4: 304>
- Purpose: Number of player4 units killed

- Note: This refers to lobby/slot/world player 4, not editor/scenario player 4

### KILLED_P5        = <Attribute.KILLED_P5: 305>
- Purpose: Number of player5 units killed

- Note: This refers to lobby/slot/world player 5, not editor/scenario player 5

### KILLED_P6        = <Attribute.KILLED_P6: 306>
- Purpose: Number of player6 units killed

- Note: This refers to lobby/slot/world player 6, not editor/scenario player 6

### KILLED_P7        = <Attribute.KILLED_P7: 307>
- Purpose: Number of player7 units killed

- Note: This refers to lobby/slot/world player 7, not editor/scenario player 7

### KILLED_P8        = <Attribute.KILLED_P8: 308>
- Purpose: Number of player8 units killed

- Note: This refers to lobby/slot/world player 8, not editor/scenario player 8

### UNUSED_RESOURCE_309        = <Attribute.UNUSED_RESOURCE_309: 309>
- Purpose: Unused

### UNUSED_RESOURCE_310        = <Attribute.UNUSED_RESOURCE_310: 310>
- Purpose: Unused

### UNUSED_RESOURCE_311        = <Attribute.UNUSED_RESOURCE_311: 311>
- Purpose: Unused

### UNUSED_RESOURCE_312        = <Attribute.UNUSED_RESOURCE_312: 312>
- Purpose: Unused

### UNUSED_RESOURCE_313        = <Attribute.UNUSED_RESOURCE_313: 313>
- Purpose: Unused

### UNUSED_RESOURCE_314        = <Attribute.UNUSED_RESOURCE_314: 314>
- Purpose: Unused

### UNUSED_RESOURCE_315        = <Attribute.UNUSED_RESOURCE_315: 315>
- Purpose: Unused

### UNUSED_RESOURCE_316        = <Attribute.UNUSED_RESOURCE_316: 316>
- Purpose: Unused

### UNUSED_RESOURCE_317        = <Attribute.UNUSED_RESOURCE_317: 317>
- Purpose: Unused

### UNUSED_RESOURCE_318        = <Attribute.UNUSED_RESOURCE_318: 318>
- Purpose: Unused

### UNUSED_RESOURCE_319        = <Attribute.UNUSED_RESOURCE_319: 319>
- Purpose: Unused

### UNUSED_RESOURCE_320        = <Attribute.UNUSED_RESOURCE_320: 320>
- Purpose: Unused

### UNUSED_RESOURCE_321        = <Attribute.UNUSED_RESOURCE_321: 321>
- Purpose: Unused

### UNUSED_RESOURCE_322        = <Attribute.UNUSED_RESOURCE_322: 322>
- Purpose: Unused

### UNUSED_RESOURCE_323        = <Attribute.UNUSED_RESOURCE_323: 323>
- Purpose: Unused

### UNUSED_RESOURCE_324        = <Attribute.UNUSED_RESOURCE_324: 324>
- Purpose: Unused

### KILLS_BY_GAIA        = <Attribute.KILLS_BY_GAIA: 325>
- Purpose: Number of own units killed by Gaia

### KILLS_BY_P1        = <Attribute.KILLS_BY_P1: 326>
- Purpose: Number of own units killed by player1

- Note: This refers to lobby/slot/world player 1, not editor/scenario player 1

### KILLS_BY_P2        = <Attribute.KILLS_BY_P2: 327>
- Purpose: Number of own units killed by player2

- Note: This refers to lobby/slot/world player 2, not editor/scenario player 2

### KILLS_BY_P3        = <Attribute.KILLS_BY_P3: 328>
- Purpose: Number of own units killed by player3

- Note: This refers to lobby/slot/world player 3, not editor/scenario player 3

### KILLS_BY_P4        = <Attribute.KILLS_BY_P4: 329>
- Purpose: Number of own units killed by player4

- Note: This refers to lobby/slot/world player 4, not editor/scenario player 4

### KILLS_BY_P5        = <Attribute.KILLS_BY_P5: 330>
- Purpose: Number of own units killed by player5

- Note: This refers to lobby/slot/world player 5, not editor/scenario player 5

### KILLS_BY_P6        = <Attribute.KILLS_BY_P6: 331>
- Purpose: Number of own units killed by player6

- Note: This refers to lobby/slot/world player 6, not editor/scenario player 6

### KILLS_BY_P7        = <Attribute.KILLS_BY_P7: 332>
- Purpose: Number of own units killed by player7

- Note: This refers to lobby/slot/world player 7, not editor/scenario player 7

### KILLS_BY_P8        = <Attribute.KILLS_BY_P8: 333>
- Purpose: Number of own units killed by player8

- Note: This refers to lobby/slot/world player 8, not editor/scenario player 8

### UNUSED_RESOURCE_334        = <Attribute.UNUSED_RESOURCE_334: 334>
- Purpose: Unused

### UNUSED_RESOURCE_335        = <Attribute.UNUSED_RESOURCE_335: 335>
- Purpose: Unused

### UNUSED_RESOURCE_336        = <Attribute.UNUSED_RESOURCE_336: 336>
- Purpose: Unused

### UNUSED_RESOURCE_337        = <Attribute.UNUSED_RESOURCE_337: 337>
- Purpose: Unused

### UNUSED_RESOURCE_338        = <Attribute.UNUSED_RESOURCE_338: 338>
- Purpose: Unused

### UNUSED_RESOURCE_339        = <Attribute.UNUSED_RESOURCE_339: 339>
- Purpose: Unused

### UNUSED_RESOURCE_340        = <Attribute.UNUSED_RESOURCE_340: 340>
- Purpose: Unused

### UNUSED_RESOURCE_341        = <Attribute.UNUSED_RESOURCE_341: 341>
- Purpose: Unused

### UNUSED_RESOURCE_342        = <Attribute.UNUSED_RESOURCE_342: 342>
- Purpose: Unused

### UNUSED_RESOURCE_343        = <Attribute.UNUSED_RESOURCE_343: 343>
- Purpose: Unused

### UNUSED_RESOURCE_344        = <Attribute.UNUSED_RESOURCE_344: 344>
- Purpose: Unused

### UNUSED_RESOURCE_345        = <Attribute.UNUSED_RESOURCE_345: 345>
- Purpose: Unused

### UNUSED_RESOURCE_346        = <Attribute.UNUSED_RESOURCE_346: 346>
- Purpose: Unused

### UNUSED_RESOURCE_347        = <Attribute.UNUSED_RESOURCE_347: 347>
- Purpose: Unused

### UNUSED_RESOURCE_348        = <Attribute.UNUSED_RESOURCE_348: 348>
- Purpose: Unused

### UNUSED_RESOURCE_349        = <Attribute.UNUSED_RESOURCE_349: 349>
- Purpose: Unused

### GAIA_RAZINGS        = <Attribute.GAIA_RAZINGS: 350>
- Purpose: Number of buildings destroyed of Gaia

### P1_RAZINGS        = <Attribute.P1_RAZINGS: 351>
- Purpose: Number of buildings destroyed of player1

- Note: This refers to lobby/slot/world player 1, not editor/scenario player 1

### P2_RAZINGS        = <Attribute.P2_RAZINGS: 352>
- Purpose: Number of buildings destroyed of player2

- Note: This refers to lobby/slot/world player 2, not editor/scenario player 2

### P3_RAZINGS        = <Attribute.P3_RAZINGS: 353>
- Purpose: Number of buildings destroyed of player3

- Note: This refers to lobby/slot/world player 3, not editor/scenario player 3

### P4_RAZINGS        = <Attribute.P4_RAZINGS: 354>
- Purpose: Number of buildings destroyed of player4

- Note: This refers to lobby/slot/world player 4, not editor/scenario player 4

### P5_RAZINGS        = <Attribute.P5_RAZINGS: 355>
- Purpose: Number of buildings destroyed of player5

- Note: This refers to lobby/slot/world player 5, not editor/scenario player 5

### P6_RAZINGS        = <Attribute.P6_RAZINGS: 356>
- Purpose: Number of buildings destroyed of player6

- Note: This refers to lobby/slot/world player 6, not editor/scenario player 6

### P7_RAZINGS        = <Attribute.P7_RAZINGS: 357>
- Purpose: Number of buildings destroyed of player7

- Note: This refers to lobby/slot/world player 7, not editor/scenario player 7

### P8_RAZINGS        = <Attribute.P8_RAZINGS: 358>
- Purpose: Number of buildings destroyed of player8

- Note: This refers to lobby/slot/world player 8, not editor/scenario player 8

### UNUSED_RESOURCE_359        = <Attribute.UNUSED_RESOURCE_359: 359>
- Purpose: Unused

### UNUSED_RESOURCE_360        = <Attribute.UNUSED_RESOURCE_360: 360>
- Purpose: Unused

### UNUSED_RESOURCE_361        = <Attribute.UNUSED_RESOURCE_361: 361>
- Purpose: Unused

### UNUSED_RESOURCE_362        = <Attribute.UNUSED_RESOURCE_362: 362>
- Purpose: Unused

### UNUSED_RESOURCE_363        = <Attribute.UNUSED_RESOURCE_363: 363>
- Purpose: Unused

### UNUSED_RESOURCE_364        = <Attribute.UNUSED_RESOURCE_364: 364>
- Purpose: Unused

### UNUSED_RESOURCE_365        = <Attribute.UNUSED_RESOURCE_365: 365>
- Purpose: Unused

### UNUSED_RESOURCE_366        = <Attribute.UNUSED_RESOURCE_366: 366>
- Purpose: Unused

### UNUSED_RESOURCE_367        = <Attribute.UNUSED_RESOURCE_367: 367>
- Purpose: Unused

### UNUSED_RESOURCE_368        = <Attribute.UNUSED_RESOURCE_368: 368>
- Purpose: Unused

### UNUSED_RESOURCE_369        = <Attribute.UNUSED_RESOURCE_369: 369>
- Purpose: Unused

### UNUSED_RESOURCE_370        = <Attribute.UNUSED_RESOURCE_370: 370>
- Purpose: Unused

### UNUSED_RESOURCE_371        = <Attribute.UNUSED_RESOURCE_371: 371>
- Purpose: Unused

### UNUSED_RESOURCE_372        = <Attribute.UNUSED_RESOURCE_372: 372>
- Purpose: Unused

### UNUSED_RESOURCE_373        = <Attribute.UNUSED_RESOURCE_373: 373>
- Purpose: Unused

### UNUSED_RESOURCE_374        = <Attribute.UNUSED_RESOURCE_374: 374>
- Purpose: Unused

### RAZINGS_BY_GAIA        = <Attribute.RAZINGS_BY_GAIA: 375>
- Purpose: Number of own buildings destroyed by Gaia

### RAZINGS_BY_P1        = <Attribute.RAZINGS_BY_P1: 376>
- Purpose: Number of own buildings destroyed by player1

- Note: This refers to lobby/slot/world player 1, not editor/scenario player 1

### RAZINGS_BY_P2        = <Attribute.RAZINGS_BY_P2: 377>
- Purpose: Number of own buildings destroyed by player2

- Note: This refers to lobby/slot/world player 2, not editor/scenario player 2

### RAZINGS_BY_P3        = <Attribute.RAZINGS_BY_P3: 378>
- Purpose: Number of own buildings destroyed by player3

- Note: This refers to lobby/slot/world player 3, not editor/scenario player 3

### RAZINGS_BY_P4        = <Attribute.RAZINGS_BY_P4: 379>
- Purpose: Number of own buildings destroyed by player4

- Note: This refers to lobby/slot/world player 4, not editor/scenario player 4

### RAZINGS_BY_P5        = <Attribute.RAZINGS_BY_P5: 380>
- Purpose: Number of own buildings destroyed by player5

- Note: This refers to lobby/slot/world player 5, not editor/scenario player 5

### RAZINGS_BY_P6        = <Attribute.RAZINGS_BY_P6: 381>
- Purpose: Number of own buildings destroyed by player6

- Note: This refers to lobby/slot/world player 6, not editor/scenario player 6

### RAZINGS_BY_P7        = <Attribute.RAZINGS_BY_P7: 382>
- Purpose: Number of own buildings destroyed by player7

- Note: This refers to lobby/slot/world player 7, not editor/scenario player 7

### RAZINGS_BY_P8        = <Attribute.RAZINGS_BY_P8: 383>
- Purpose: Number of own buildings destroyed by player8

- Note: This refers to lobby/slot/world player 8, not editor/scenario player 8

### UNUSED_RESOURCE_384        = <Attribute.UNUSED_RESOURCE_384: 384>
- Purpose: Unused

### UNUSED_RESOURCE_385        = <Attribute.UNUSED_RESOURCE_385: 385>
- Purpose: Unused

### UNUSED_RESOURCE_386        = <Attribute.UNUSED_RESOURCE_386: 386>
- Purpose: Unused

### UNUSED_RESOURCE_387        = <Attribute.UNUSED_RESOURCE_387: 387>
- Purpose: Unused

### UNUSED_RESOURCE_388        = <Attribute.UNUSED_RESOURCE_388: 388>
- Purpose: Unused

### UNUSED_RESOURCE_389        = <Attribute.UNUSED_RESOURCE_389: 389>
- Purpose: Unused

### UNUSED_RESOURCE_390        = <Attribute.UNUSED_RESOURCE_390: 390>
- Purpose: Unused

### UNUSED_RESOURCE_391        = <Attribute.UNUSED_RESOURCE_391: 391>
- Purpose: Unused

### UNUSED_RESOURCE_392        = <Attribute.UNUSED_RESOURCE_392: 392>
- Purpose: Unused

### UNUSED_RESOURCE_393        = <Attribute.UNUSED_RESOURCE_393: 393>
- Purpose: Unused

### UNUSED_RESOURCE_394        = <Attribute.UNUSED_RESOURCE_394: 394>
- Purpose: Unused

### UNUSED_RESOURCE_395        = <Attribute.UNUSED_RESOURCE_395: 395>
- Purpose: Unused

### UNUSED_RESOURCE_396        = <Attribute.UNUSED_RESOURCE_396: 396>
- Purpose: Unused

### UNUSED_RESOURCE_397        = <Attribute.UNUSED_RESOURCE_397: 397>
- Purpose: Unused

### UNUSED_RESOURCE_398        = <Attribute.UNUSED_RESOURCE_398: 398>
- Purpose: Unused

### UNUSED_RESOURCE_399        = <Attribute.UNUSED_RESOURCE_399: 399>
- Purpose: Unused

### GAIA_KILL_VALUE        = <Attribute.GAIA_KILL_VALUE: 400>
- Purpose: Total cost of all units killed of Gaia

### P1_KILL_VALUE        = <Attribute.P1_KILL_VALUE: 401>
- Purpose: Total cost of all units killed of player1

- Note: This refers to lobby/slot/world player 1, not editor/scenario player 1

### P2_KILL_VALUE        = <Attribute.P2_KILL_VALUE: 402>
- Purpose: Total cost of all units killed of player2

- Note: This refers to lobby/slot/world player 2, not editor/scenario player 2

### P3_KILL_VALUE        = <Attribute.P3_KILL_VALUE: 403>
- Purpose: Total cost of all units killed of player3

- Note: This refers to lobby/slot/world player 3, not editor/scenario player 3

### P4_KILL_VALUE        = <Attribute.P4_KILL_VALUE: 404>
- Purpose: Total cost of all units killed of player4

- Note: This refers to lobby/slot/world player 4, not editor/scenario player 4

### P5_KILL_VALUE        = <Attribute.P5_KILL_VALUE: 405>
- Purpose: Total cost of all units killed of player5

- Note: This refers to lobby/slot/world player 5, not editor/scenario player 5

### P6_KILL_VALUE        = <Attribute.P6_KILL_VALUE: 406>
- Purpose: Total cost of all units killed of player6

- Note: This refers to lobby/slot/world player 6, not editor/scenario player 6

### P7_KILL_VALUE        = <Attribute.P7_KILL_VALUE: 407>
- Purpose: Total cost of all units killed of player7

- Note: This refers to lobby/slot/world player 7, not editor/scenario player 7

### P8_KILL_VALUE        = <Attribute.P8_KILL_VALUE: 408>
- Purpose: Total cost of all units killed of player8

- Note: This refers to lobby/slot/world player 8, not editor/scenario player 8

### UNUSED_RESOURCE_409        = <Attribute.UNUSED_RESOURCE_409: 409>
- Purpose: Unused

### UNUSED_RESOURCE_410        = <Attribute.UNUSED_RESOURCE_410: 410>
- Purpose: Unused

### UNUSED_RESOURCE_411        = <Attribute.UNUSED_RESOURCE_411: 411>
- Purpose: Unused

### UNUSED_RESOURCE_412        = <Attribute.UNUSED_RESOURCE_412: 412>
- Purpose: Unused

### UNUSED_RESOURCE_413        = <Attribute.UNUSED_RESOURCE_413: 413>
- Purpose: Unused

### UNUSED_RESOURCE_414        = <Attribute.UNUSED_RESOURCE_414: 414>
- Purpose: Unused

### UNUSED_RESOURCE_415        = <Attribute.UNUSED_RESOURCE_415: 415>
- Purpose: Unused

### UNUSED_RESOURCE_416        = <Attribute.UNUSED_RESOURCE_416: 416>
- Purpose: Unused

### UNUSED_RESOURCE_417        = <Attribute.UNUSED_RESOURCE_417: 417>
- Purpose: Unused

### UNUSED_RESOURCE_418        = <Attribute.UNUSED_RESOURCE_418: 418>
- Purpose: Unused

### UNUSED_RESOURCE_419        = <Attribute.UNUSED_RESOURCE_419: 419>
- Purpose: Unused

### UNUSED_RESOURCE_420        = <Attribute.UNUSED_RESOURCE_420: 420>
- Purpose: Unused

### UNUSED_RESOURCE_421        = <Attribute.UNUSED_RESOURCE_421: 421>
- Purpose: Unused

### UNUSED_RESOURCE_422        = <Attribute.UNUSED_RESOURCE_422: 422>
- Purpose: Unused

### UNUSED_RESOURCE_423        = <Attribute.UNUSED_RESOURCE_423: 423>
- Purpose: Unused

### UNUSED_RESOURCE_424        = <Attribute.UNUSED_RESOURCE_424: 424>
- Purpose: Unused

### GAIA_RAZING_VALUE        = <Attribute.GAIA_RAZING_VALUE: 425>
- Purpose: Total cost of all buildings destroyed of Gaia

### P1_RAZING_VALUE        = <Attribute.P1_RAZING_VALUE: 426>
- Purpose: Total cost of all buildings destroyed of player1

- Note: This refers to lobby/slot/world player 1, not editor/scenario player 1

### P2_RAZING_VALUE        = <Attribute.P2_RAZING_VALUE: 427>
- Purpose: Total cost of all buildings destroyed of player2

- Note: This refers to lobby/slot/world player 2, not editor/scenario player 2

### P3_RAZING_VALUE        = <Attribute.P3_RAZING_VALUE: 428>
- Purpose: Total cost of all buildings destroyed of player3

- Note: This refers to lobby/slot/world player 3, not editor/scenario player 3

### P4_RAZING_VALUE        = <Attribute.P4_RAZING_VALUE: 429>
- Purpose: Total cost of all buildings destroyed of player4

- Note: This refers to lobby/slot/world player 4, not editor/scenario player 4

### P5_RAZING_VALUE        = <Attribute.P5_RAZING_VALUE: 430>
- Purpose: Total cost of all buildings destroyed of player5

- Note: This refers to lobby/slot/world player 5, not editor/scenario player 5

### P6_RAZING_VALUE        = <Attribute.P6_RAZING_VALUE: 431>
- Purpose: Total cost of all buildings destroyed of player6

- Note: This refers to lobby/slot/world player 6, not editor/scenario player 6

### P7_RAZING_VALUE        = <Attribute.P7_RAZING_VALUE: 432>
- Purpose: Total cost of all buildings destroyed of player7

- Note: This refers to lobby/slot/world player 7, not editor/scenario player 7

### P8_RAZING_VALUE        = <Attribute.P8_RAZING_VALUE: 433>
- Purpose: Total cost of all buildings destroyed of player8

- Note: This refers to lobby/slot/world player 8, not editor/scenario player 8

### UNUSED_RESOURCE_434        = <Attribute.UNUSED_RESOURCE_434: 434>
- Purpose: Unused

### UNUSED_RESOURCE_435        = <Attribute.UNUSED_RESOURCE_435: 435>
- Purpose: Unused

### UNUSED_RESOURCE_436        = <Attribute.UNUSED_RESOURCE_436: 436>
- Purpose: Unused

### UNUSED_RESOURCE_437        = <Attribute.UNUSED_RESOURCE_437: 437>
- Purpose: Unused

### UNUSED_RESOURCE_438        = <Attribute.UNUSED_RESOURCE_438: 438>
- Purpose: Unused

### UNUSED_RESOURCE_439        = <Attribute.UNUSED_RESOURCE_439: 439>
- Purpose: Unused

### UNUSED_RESOURCE_440        = <Attribute.UNUSED_RESOURCE_440: 440>
- Purpose: Unused

### UNUSED_RESOURCE_441        = <Attribute.UNUSED_RESOURCE_441: 441>
- Purpose: Unused

### UNUSED_RESOURCE_442        = <Attribute.UNUSED_RESOURCE_442: 442>
- Purpose: Unused

### UNUSED_RESOURCE_443        = <Attribute.UNUSED_RESOURCE_443: 443>
- Purpose: Unused

### UNUSED_RESOURCE_444        = <Attribute.UNUSED_RESOURCE_444: 444>
- Purpose: Unused

### UNUSED_RESOURCE_445        = <Attribute.UNUSED_RESOURCE_445: 445>
- Purpose: Unused

### UNUSED_RESOURCE_446        = <Attribute.UNUSED_RESOURCE_446: 446>
- Purpose: Unused

### UNUSED_RESOURCE_447        = <Attribute.UNUSED_RESOURCE_447: 447>
- Purpose: Unused

### UNUSED_RESOURCE_448        = <Attribute.UNUSED_RESOURCE_448: 448>
- Purpose: Unused

### UNUSED_RESOURCE_449        = <Attribute.UNUSED_RESOURCE_449: 449>
- Purpose: Unused

### GAIA_TRIBUTE        = <Attribute.GAIA_TRIBUTE: 450>
- Purpose: Amount of resources tributed to Gaia

### P1_TRIBUTE        = <Attribute.P1_TRIBUTE: 451>
- Purpose: Amount of resources tributed to player1

- Note: This refers to lobby/slot/world player 1, not editor/scenario player 1

### P2_TRIBUTE        = <Attribute.P2_TRIBUTE: 452>
- Purpose: Amount of resources tributed to player2

- Note: This refers to lobby/slot/world player 2, not editor/scenario player 2

### P3_TRIBUTE        = <Attribute.P3_TRIBUTE: 453>
- Purpose: Amount of resources tributed to player3

- Note: This refers to lobby/slot/world player 3, not editor/scenario player 3

### P4_TRIBUTE        = <Attribute.P4_TRIBUTE: 454>
- Purpose: Amount of resources tributed to player4

- Note: This refers to lobby/slot/world player 4, not editor/scenario player 4

### P5_TRIBUTE        = <Attribute.P5_TRIBUTE: 455>
- Purpose: Amount of resources tributed to player5

- Note: This refers to lobby/slot/world player 5, not editor/scenario player 5

### P6_TRIBUTE        = <Attribute.P6_TRIBUTE: 456>
- Purpose: Amount of resources tributed to player6

- Note: This refers to lobby/slot/world player 6, not editor/scenario player 6

### P7_TRIBUTE        = <Attribute.P7_TRIBUTE: 457>
- Purpose: Amount of resources tributed to player7

- Note: This refers to lobby/slot/world player 7, not editor/scenario player 7

### P8_TRIBUTE        = <Attribute.P8_TRIBUTE: 458>
- Purpose: Amount of resources tributed to player8

- Note: This refers to lobby/slot/world player 8, not editor/scenario player 8

### UNUSED_RESOURCE_459        = <Attribute.UNUSED_RESOURCE_459: 459>
- Purpose: Unused

### UNUSED_RESOURCE_460        = <Attribute.UNUSED_RESOURCE_460: 460>
- Purpose: Unused

### UNUSED_RESOURCE_461        = <Attribute.UNUSED_RESOURCE_461: 461>
- Purpose: Unused

### UNUSED_RESOURCE_462        = <Attribute.UNUSED_RESOURCE_462: 462>
- Purpose: Unused

### UNUSED_RESOURCE_463        = <Attribute.UNUSED_RESOURCE_463: 463>
- Purpose: Unused

### UNUSED_RESOURCE_464        = <Attribute.UNUSED_RESOURCE_464: 464>
- Purpose: Unused

### UNUSED_RESOURCE_465        = <Attribute.UNUSED_RESOURCE_465: 465>
- Purpose: Unused

### UNUSED_RESOURCE_466        = <Attribute.UNUSED_RESOURCE_466: 466>
- Purpose: Unused

### UNUSED_RESOURCE_467        = <Attribute.UNUSED_RESOURCE_467: 467>
- Purpose: Unused

### UNUSED_RESOURCE_468        = <Attribute.UNUSED_RESOURCE_468: 468>
- Purpose: Unused

### UNUSED_RESOURCE_469        = <Attribute.UNUSED_RESOURCE_469: 469>
- Purpose: Unused

### UNUSED_RESOURCE_470        = <Attribute.UNUSED_RESOURCE_470: 470>
- Purpose: Unused

### UNUSED_RESOURCE_471        = <Attribute.UNUSED_RESOURCE_471: 471>
- Purpose: Unused

### UNUSED_RESOURCE_472        = <Attribute.UNUSED_RESOURCE_472: 472>
- Purpose: Unused

### UNUSED_RESOURCE_473        = <Attribute.UNUSED_RESOURCE_473: 473>
- Purpose: Unused

### UNUSED_RESOURCE_474        = <Attribute.UNUSED_RESOURCE_474: 474>
- Purpose: Unused

### TRIBUTE_FROM_GAIA        = <Attribute.TRIBUTE_FROM_GAIA: 475>
- Purpose: Tribute received from Gaia

### TRIBUTE_FROM_P1        = <Attribute.TRIBUTE_FROM_P1: 476>
- Purpose: Tribute received from player1

- Note: This refers to lobby/slot/world player 1, not editor/scenario player 1

### TRIBUTE_FROM_P2        = <Attribute.TRIBUTE_FROM_P2: 477>
- Purpose: Tribute received from player2

- Note: This refers to lobby/slot/world player 2, not editor/scenario player 2

### TRIBUTE_FROM_P3        = <Attribute.TRIBUTE_FROM_P3: 478>
- Purpose: Tribute received from player3

- Note: This refers to lobby/slot/world player 3, not editor/scenario player 3

### TRIBUTE_FROM_P4        = <Attribute.TRIBUTE_FROM_P4: 479>
- Purpose: Tribute received from player4

- Note: This refers to lobby/slot/world player 4, not editor/scenario player 4

### TRIBUTE_FROM_P5        = <Attribute.TRIBUTE_FROM_P5: 480>
- Purpose: Tribute received from player5

- Note: This refers to lobby/slot/world player 5, not editor/scenario player 5

### TRIBUTE_FROM_P6        = <Attribute.TRIBUTE_FROM_P6: 481>
- Purpose: Tribute received from player6

- Note: This refers to lobby/slot/world player 6, not editor/scenario player 6

### TRIBUTE_FROM_P7        = <Attribute.TRIBUTE_FROM_P7: 482>
- Purpose: Tribute received from player7

- Note: This refers to lobby/slot/world player 7, not editor/scenario player 7

### TRIBUTE_FROM_P8        = <Attribute.TRIBUTE_FROM_P8: 483>
- Purpose: Tribute received from player8

- Note: This refers to lobby/slot/world player 8, not editor/scenario player 8

### UNUSED_RESOURCE_484        = <Attribute.UNUSED_RESOURCE_484: 484>
- Purpose: Unused

### UNUSED_RESOURCE_485        = <Attribute.UNUSED_RESOURCE_485: 485>
- Purpose: Unused

### UNUSED_RESOURCE_486        = <Attribute.UNUSED_RESOURCE_486: 486>
- Purpose: Unused

### UNUSED_RESOURCE_487        = <Attribute.UNUSED_RESOURCE_487: 487>
- Purpose: Unused

### UNUSED_RESOURCE_488        = <Attribute.UNUSED_RESOURCE_488: 488>
- Purpose: Unused

### UNUSED_RESOURCE_489        = <Attribute.UNUSED_RESOURCE_489: 489>
- Purpose: Unused

### UNUSED_RESOURCE_490        = <Attribute.UNUSED_RESOURCE_490: 490>
- Purpose: Unused

### UNUSED_RESOURCE_491        = <Attribute.UNUSED_RESOURCE_491: 491>
- Purpose: Unused

### UNUSED_RESOURCE_492        = <Attribute.UNUSED_RESOURCE_492: 492>
- Purpose: Unused

### UNUSED_RESOURCE_493        = <Attribute.UNUSED_RESOURCE_493: 493>
- Purpose: Unused

### UNUSED_RESOURCE_494        = <Attribute.UNUSED_RESOURCE_494: 494>
- Purpose: Unused

### UNUSED_RESOURCE_495        = <Attribute.UNUSED_RESOURCE_495: 495>
- Purpose: Unused

### UNUSED_RESOURCE_496        = <Attribute.UNUSED_RESOURCE_496: 496>
- Purpose: Unused

### UNUSED_RESOURCE_497        = <Attribute.UNUSED_RESOURCE_497: 497>
- Purpose: Unused

### UNUSED_RESOURCE_498        = <Attribute.UNUSED_RESOURCE_498: 498>
- Purpose: Unused

### UNUSED_RESOURCE_499        = <Attribute.UNUSED_RESOURCE_499: 499>
- Purpose: Unused

### UNUSED_RESOURCE_500        = <Attribute.UNUSED_RESOURCE_500: 500>
- Purpose: Unused

### POLEMARCH_BUILD_LIMIT        = <Attribute.POLEMARCH_BUILD_LIMIT: 501>
- Purpose: Hidden resource that is part of the cost of Polemarch. Incremented when the Polemarch dies, decremented when a Polemarch is trained. Increment this value to allow training of more Polemarchs

- Defaults:

- 0: Default

### ATHENIAN_CHOPPING_FOOD_PRODUCTIVITY        = <Attribute.ATHENIAN_CHOPPING_FOOD_PRODUCTIVITY: 502>
- Purpose: Chopping food gathering percent of main work rate

- Defaults:

- 0: Default

- 4: Athenians

- 7: Shu

- Note: EffectFunction16 must be called for this resource to work. While the name only contains Athenians, this resource is also used for Shu.

### WOOD_TRADE_RATIO        = <Attribute.WOOD_TRADE_RATIO: 503>
- Purpose: Amount of trade will be returned as wood instead of gold.

- Defaults:

- 0: Default

- 0.25: Achaemenids, Athenians and Spartans.

- Note: Changed in the Battle of Greece civs Port by a toggle to 0.25, 0.5, and 0.75 or by researching equivalent tech in the editor. Setting it to 0.5 will return half the amount in gold and half in wood. Works for trade cogs only. Setting it to a value >= 1 will make it so no trade resources are returned.

### UNUSED_RESOURCE_504        = <Attribute.UNUSED_RESOURCE_504: 504>
- Purpose: Unused but civs start with 1 at the start of the game. Also unused Spanish team bonus effect multiplies its value by 0.8

- Defaults:

- 1: At the start of the game. Does not seem to do anything

### UNUSED_RESOURCE_505        = <Attribute.UNUSED_RESOURCE_505: 505>
- Purpose: Unused, but Achaemenids, Athenians and Spartans have it set to 1

- Defaults:

- 0: Default

- 1: Achaemenids, Athenians and Spartans

### ACHAEMENID_TOWN_CENTER_LOCAL_UPGRADE        = <Attribute.ACHAEMENID_TOWN_CENTER_LOCAL_UPGRADE: 506>
- Purpose: Used as a local resource in Town Centers to know which of them have the Achamenids Town Center upgrade researched

- Defaults:

- 0: Default

- 1: Achaemenids, Athenians and Spartans

- Note: Achamenids Town Center Local Upgrade resource is changed when its tech is researched. As a side effect its global player value will be decremented every time a Town Center is destroyed.

### UNUSED_RESOURCE_507        = <Attribute.UNUSED_RESOURCE_507: 507>
- Purpose: Unused, but Athenians Static Bonuses effect sets it to 1

- Defaults:

- 0: Default

- 1: Athenians

- Note: Athenians start with it set to 1 by initial Economic Policy.

### FORTIFIED_OUTPOST_LOCAL_UPGRADE        = <Attribute.FORTIFIED_OUTPOST_LOCAL_UPGRADE: 508>
- Purpose: Used as a local resource in Outposts

- Note: Fortified Outpost Local Upgrade resource is changed when its tech is researched. As a side effect its global player value will be decremented every time an Outpost is destroyed.

### MERCENARY_HOPLITE_PRODUCTIVITY        = <Attribute.MERCENARY_HOPLITE_PRODUCTIVITY: 509>
- Purpose: It is named in the editor but seems to no longer affect Mercenary Hoplite and therefore unused

### ODOMANTIAN_RAIDERS_PRODUCTIVITY        = <Attribute.ODOMANTIAN_RAIDERS_PRODUCTIVITY: 510>
- Purpose: Modifies how much gold units gain affected by Odomantian Raiders tech

- Defaults:

- 0: Default

- 1: Spartans or after Odomantian Raiders is researched

### DII_PLUNDERERS_PRODUCTIVITY        = <Attribute.DII_PLUNDERERS_PRODUCTIVITY: 511>
- Purpose: Modifies how much resources units gain affected by Dii Plunderers tech

- Defaults:

- 0: Default

- 1: After Dii Plunderers is researched

### STONE_MINING_FOOD_PRODUCTIVITY        = <Attribute.STONE_MINING_FOOD_PRODUCTIVITY: 512>
- Purpose: Stone mining food generation rate

- Defaults:

- 0: Default

- 1: Puru

### EMPLACEMENT_LOCAL_UPGRADE        = <Attribute.EMPLACEMENT_LOCAL_UPGRADE: 513>
- Purpose: Used as a local cost to upgrade Fort to an emplacement

### HELEPOLIS_LIMIT        = <Attribute.HELEPOLIS_LIMIT: 514>
- Purpose: Limit the amount of Helepolis that can be built. Only works if Helepolis are built as buildings

### SCYTHIAN_HORSE_ARCHER_PRODUCTIVITY        = <Attribute.SCYTHIAN_HORSE_ARCHER_PRODUCTIVITY: 515>
- Purpose: Modifies how much gold Scythian Horse Archer and Elite Scythian Horse Archer gain when killing units

- Defaults:

- 1: Default

- 0: Shu, Wu, Wei, Jurchens, Khitans

### UNUSED_RESOURCE_516        = <Attribute.UNUSED_RESOURCE_516: 516>
- Purpose: Unused

### UNUSED_RESOURCE_517        = <Attribute.UNUSED_RESOURCE_517: 517>
- Purpose: Unused

### UNUSED_RESOURCE_518        = <Attribute.UNUSED_RESOURCE_518: 518>
- Purpose: Unused

### UNUSED_RESOURCE_519        = <Attribute.UNUSED_RESOURCE_519: 519>
- Purpose: Unused

### LYSANDERS_RAIDER_PRODUCTIVITY        = <Attribute.LYSANDERS_RAIDER_PRODUCTIVITY: 520>
- Purpose: Modifies how much gold Lysanders Raider gains when killing units

- Defaults:

- 1: Default

### PELOPONNESIAN_LEAGUE_PRODUCTIVITY        = <Attribute.PELOPONNESIAN_LEAGUE_PRODUCTIVITY: 521>
- Purpose: Castle gold production rate multiplier

- Defaults:

- 0: Default

- 1: After Peloponnesian League researched

- Note: The amount of gold obtained from owning n number of Castles is given by n * castle_gold_productivity * 0.33333.

### BASE_HOPLITE_AURA_ENABLED        = <Attribute.BASE_HOPLITE_AURA_ENABLED: 522>
- Purpose: Turns on base Hoplite aura

- Defaults:

- 1: Default

- 0: Macedonians, Thracians, Puru or after Agoge is researched

### AGOGE_HOPLITE_AURA_ENABLED        = <Attribute.AGOGE_HOPLITE_AURA_ENABLED: 523>
- Purpose: Turns on aura gained via Agoge tech for Hoplites

- Defaults:

- 1: After Agoge is researched

- 0: Default

### XYPHOS_HOPLITE_AURA_ENABLED        = <Attribute.XYPHOS_HOPLITE_AURA_ENABLED: 524>
- Purpose: Turns on aura gained via Xyphos tech for Hoplites

- Defaults:

- 1: After Xyphos is researched

- 0: Default

### BASE_STRATEGOS_AURA_ENABLED        = <Attribute.BASE_STRATEGOS_AURA_ENABLED: 525>
- Purpose: Turns on base Strategos aura

- Defaults:

- 1: Default

- 0: Macedonians, Thracians, Puru or after Taxiarchs is researched

### TAXIARCHS_STRATEGOS_AURA_ENABLED        = <Attribute.TAXIARCHS_STRATEGOS_AURA_ENABLED: 526>
- Purpose: Turns on aura gained via Taxiarchs tech for Strategos

- Defaults:

- 1: After Taxiarchs is researched

- 0: Default

### HIPPEUS_AURA_NO_TECH        = <Attribute.HIPPEUS_AURA_NO_TECH: 527>
- Purpose: Turns on base Hippeus aura

- Defaults:

- 1: Default

- 0: Macedonians, Thracians, Puru or after Morai is researched

### HIPPEUS_AURA_WITH_TECHS        = <Attribute.HIPPEUS_AURA_WITH_TECHS: 528>
- Purpose: Turns on aura gained via Morai tech for Hippeus

- Defaults:

- 1: After Morai is researched

- 0: Default

### UNUSED_RESOURCE_529        = <Attribute.UNUSED_RESOURCE_529: 529>
- Purpose: Unused

### UNUSED_RESOURCE_530        = <Attribute.UNUSED_RESOURCE_530: 530>
- Purpose: Unused

### SCENARIO_RESOURCE_01        = <Attribute.SCENARIO_RESOURCE_01: 531>
- Purpose: Unused

### SCENARIO_RESOURCE_02        = <Attribute.SCENARIO_RESOURCE_02: 532>
- Purpose: Unused

### SCENARIO_RESOURCE_03        = <Attribute.SCENARIO_RESOURCE_03: 533>
- Purpose: Unused

### SCENARIO_RESOURCE_04        = <Attribute.SCENARIO_RESOURCE_04: 534>
- Purpose: Unused

### SCENARIO_RESOURCE_05        = <Attribute.SCENARIO_RESOURCE_05: 535>
- Purpose: Unused

### SCENARIO_RESOURCE_06        = <Attribute.SCENARIO_RESOURCE_06: 536>
- Purpose: Unused

### SCENARIO_RESOURCE_07        = <Attribute.SCENARIO_RESOURCE_07: 537>
- Purpose: Unused

### SCENARIO_RESOURCE_08        = <Attribute.SCENARIO_RESOURCE_08: 538>
- Purpose: Unused

### SCENARIO_RESOURCE_09        = <Attribute.SCENARIO_RESOURCE_09: 539>
- Purpose: Unused

### SCENARIO_RESOURCE_10        = <Attribute.SCENARIO_RESOURCE_10: 540>
- Purpose: Unused

### SCENARIO_RESOURCE_11        = <Attribute.SCENARIO_RESOURCE_11: 541>
- Purpose: Unused

### SCENARIO_RESOURCE_12        = <Attribute.SCENARIO_RESOURCE_12: 542>
- Purpose: Unused

### SCENARIO_RESOURCE_13        = <Attribute.SCENARIO_RESOURCE_13: 543>
- Purpose: Unused

### SCENARIO_RESOURCE_14        = <Attribute.SCENARIO_RESOURCE_14: 544>
- Purpose: Unused

### SCENARIO_RESOURCE_15        = <Attribute.SCENARIO_RESOURCE_15: 545>
- Purpose: Unused

### SCENARIO_RESOURCE_16        = <Attribute.SCENARIO_RESOURCE_16: 546>
- Purpose: Unused

### SCENARIO_RESOURCE_17        = <Attribute.SCENARIO_RESOURCE_17: 547>
- Purpose: Unused

### UNUSED_RESOURCE_548        = <Attribute.UNUSED_RESOURCE_548: 548>
- Purpose: Unused

### UNUSED_RESOURCE_549        = <Attribute.UNUSED_RESOURCE_549: 549>
- Purpose: Unused

### CAMEL_RAIDER_PRODUCTIVITY        = <Attribute.CAMEL_RAIDER_PRODUCTIVITY: 550>
- Purpose: Modifies how much gold Lysander's Raider and Camel Raider gain when killing units

- Defaults:

- 1: Default

### TYRANNY_PRODUCTIVITY        = <Attribute.TYRANNY_PRODUCTIVITY: 551>
- Purpose: Gain gold per unit killed

- Defaults:

- 0: Default

- 1: After Military Policy activated

- Note: The amount of gold obtained from killing number of units u is u * unit_loot_productivity * 3. Unlike resources 520 and 550 works on most units. Look at A.G.E. for units with 154 loot class task.

### UNUSED_RESOURCE_552        = <Attribute.UNUSED_RESOURCE_552: 552>
- Purpose: Unused

### UNUSED_RESOURCE_553        = <Attribute.UNUSED_RESOURCE_553: 553>
- Purpose: Unused

### UNUSED_RESOURCE_554        = <Attribute.UNUSED_RESOURCE_554: 554>
- Purpose: Unused

### UNUSED_RESOURCE_555        = <Attribute.UNUSED_RESOURCE_555: 555>
- Purpose: Unused

### UNUSED_RESOURCE_556        = <Attribute.UNUSED_RESOURCE_556: 556>
- Purpose: Unused

### UNUSED_RESOURCE_557        = <Attribute.UNUSED_RESOURCE_557: 557>
- Purpose: Unused

### UNUSED_RESOURCE_558        = <Attribute.UNUSED_RESOURCE_558: 558>
- Purpose: Unused

### UNUSED_RESOURCE_559        = <Attribute.UNUSED_RESOURCE_559: 559>
- Purpose: Unused

### ENDS_OF_THE_WORLD_PRODUCTIVITY        = <Attribute.ENDS_OF_THE_WORLD_PRODUCTIVITY: 560>
- Purpose: Turns on aura gained via Ends of the World tech for Fortified Outpost

### PATTIYODHA_LONGBOWMAN_DEFAULT        = <Attribute.PATTIYODHA_LONGBOWMAN_DEFAULT: 561>
- Purpose: Turns on base Pattiyodha Longbowman aura

- Defaults:

- 1: Default

- 0: Macedonians, Thracians, Puru or after Leaf-Headed Shafts is researched

### PATTIYODHA_LONGBOWMAN_UPGRADED        = <Attribute.PATTIYODHA_LONGBOWMAN_UPGRADED: 562>
- Purpose: Turns on aura gained via Leaf-Headed Shafts tech for Pattiyodha Longbowman

- Defaults:

- 1: After Leaf-Headed Shafts is researched

- 0: Default

### SHEPHERD_GOLD_PRODUCTIVITY        = <Attribute.SHEPHERD_GOLD_PRODUCTIVITY: 563>
- Purpose: Sheep herding and hunting gold generation rate

- Defaults:

- 0: Default

- 1: Thracians

### UNUSED_RESOURCE_564        = <Attribute.UNUSED_RESOURCE_564: 564>
- Purpose: Unused

### UNUSED_RESOURCE_565        = <Attribute.UNUSED_RESOURCE_565: 565>
- Purpose: Unused

### UNUSED_RESOURCE_566        = <Attribute.UNUSED_RESOURCE_566: 566>
- Purpose: Unused

### UNUSED_RESOURCE_567        = <Attribute.UNUSED_RESOURCE_567: 567>
- Purpose: Unused

### UNUSED_RESOURCE_568        = <Attribute.UNUSED_RESOURCE_568: 568>
- Purpose: Unused

### UNUSED_RESOURCE_569        = <Attribute.UNUSED_RESOURCE_569: 569>
- Purpose: Unused

### UNUSED_RESOURCE_570        = <Attribute.UNUSED_RESOURCE_570: 570>
- Purpose: Unused

### UNUSED_RESOURCE_571        = <Attribute.UNUSED_RESOURCE_571: 571>
- Purpose: Unused

### UNUSED_RESOURCE_572        = <Attribute.UNUSED_RESOURCE_572: 572>
- Purpose: Unused

### UNUSED_RESOURCE_573        = <Attribute.UNUSED_RESOURCE_573: 573>
- Purpose: Unused

### UNUSED_RESOURCE_574        = <Attribute.UNUSED_RESOURCE_574: 574>
- Purpose: Unused

### UNUSED_RESOURCE_575        = <Attribute.UNUSED_RESOURCE_575: 575>
- Purpose: Unused

### UNUSED_RESOURCE_576        = <Attribute.UNUSED_RESOURCE_576: 576>
- Purpose: Unused

### UNUSED_RESOURCE_577        = <Attribute.UNUSED_RESOURCE_577: 577>
- Purpose: Unused

### UNUSED_RESOURCE_578        = <Attribute.UNUSED_RESOURCE_578: 578>
- Purpose: Unused

### UNUSED_RESOURCE_579        = <Attribute.UNUSED_RESOURCE_579: 579>
- Purpose: Unused

### UNUSED_RESOURCE_580        = <Attribute.UNUSED_RESOURCE_580: 580>
- Purpose: Unused

### UNUSED_RESOURCE_581        = <Attribute.UNUSED_RESOURCE_581: 581>
- Purpose: Unused

### UNUSED_RESOURCE_582        = <Attribute.UNUSED_RESOURCE_582: 582>
- Purpose: Unused

### UNUSED_RESOURCE_583        = <Attribute.UNUSED_RESOURCE_583: 583>
- Purpose: Unused

### UNUSED_RESOURCE_584        = <Attribute.UNUSED_RESOURCE_584: 584>
- Purpose: Unused

### UNUSED_RESOURCE_585        = <Attribute.UNUSED_RESOURCE_585: 585>
- Purpose: Unused

### UNUSED_RESOURCE_586        = <Attribute.UNUSED_RESOURCE_586: 586>
- Purpose: Unused

### UNUSED_RESOURCE_587        = <Attribute.UNUSED_RESOURCE_587: 587>
- Purpose: Unused

### UNUSED_RESOURCE_588        = <Attribute.UNUSED_RESOURCE_588: 588>
- Purpose: Unused

### UNUSED_RESOURCE_589        = <Attribute.UNUSED_RESOURCE_589: 589>
- Purpose: Unused

### UNUSED_RESOURCE_590        = <Attribute.UNUSED_RESOURCE_590: 590>
- Purpose: Unused

### UNUSED_RESOURCE_591        = <Attribute.UNUSED_RESOURCE_591: 591>
- Purpose: Unused

### UNUSED_RESOURCE_592        = <Attribute.UNUSED_RESOURCE_592: 592>
- Purpose: Unused

### UNUSED_RESOURCE_593        = <Attribute.UNUSED_RESOURCE_593: 593>
- Purpose: Unused

### UNUSED_RESOURCE_594        = <Attribute.UNUSED_RESOURCE_594: 594>
- Purpose: Unused

### UNUSED_RESOURCE_595        = <Attribute.UNUSED_RESOURCE_595: 595>
- Purpose: Unused

### UNUSED_RESOURCE_596        = <Attribute.UNUSED_RESOURCE_596: 596>
- Purpose: Unused

### UNUSED_RESOURCE_597        = <Attribute.UNUSED_RESOURCE_597: 597>
- Purpose: Unused

### UNUSED_RESOURCE_598        = <Attribute.UNUSED_RESOURCE_598: 598>
- Purpose: Unused

### UNUSED_RESOURCE_599        = <Attribute.UNUSED_RESOURCE_599: 599>
- Purpose: Unused

### UNUSED_RESOURCE_600        = <Attribute.UNUSED_RESOURCE_600: 600>
- Purpose: Unused


### class     BlastLevel(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the blast level values used in the game. Used in the
'Modify Attribute' effect with the 'Blast Attack/Defense Level' attributes

Examples

### RESOURCES        = <BlastLevel.RESOURCES: 0>
damage resources, nearby allied units and tress

### TREES        = <BlastLevel.TREES: 1>
damage trees, nearby allied units

### NEARBY_UNITS        = <BlastLevel.NEARBY_UNITS: 2>
damage nearby allied units

### TARGET_ONLY        = <BlastLevel.TARGET_ONLY: 3>
damage targeted unit only

### FIXED_FIVE        = <BlastLevel.FIXED_FIVE: 4>
Deal a fixed 5 HP of damage to nearby units

### IGNORE_FRIENDLY_FIRE        = <BlastLevel.IGNORE_FRIENDLY_FIRE: 8>
Ignore friendly fire

### DISTANCE_ATTENUATION        = <BlastLevel.DISTANCE_ATTENUATION: 64>
Attenuate damage as distance from the centre of attack increases (infantry only)

### DIRECTIONAL        = <BlastLevel.DIRECTIONAL: 128>
Blast damage is dealt along the direction the unit is facing only. This area is a very narrow cone


### class     BlockageClass(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values for the different blockage classes that can be used in the 'Modify
Attribute' effect with the 'BlockageClass' attribute.

Examples:

### DEFAULT        = <BlockageClass.DEFAULT: 0>
Forces default obstruction type

### RESOURCE        = <BlockageClass.RESOURCE: 1>

### UNIT        = <BlockageClass.UNIT: 2>

### BUILDING        = <BlockageClass.BUILDING: 3>

### WALL        = <BlockageClass.WALL: 4>

### GATE        = <BlockageClass.GATE: 5>
Gate, allows trespassing

### CLIFF        = <BlockageClass.CLIFF: 6>
Cliff, blocks walling


### class     ButtonLocation(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the button locations in the game. These button
locations are what determines where a unit's train button or a research's research button appears in a building's
UI

Examples

### r1c1        = <ButtonLocation.r1c1: 1>

### r1c2        = <ButtonLocation.r1c2: 2>

### r1c3        = <ButtonLocation.r1c3: 3>

### r1c4        = <ButtonLocation.r1c4: 4>

### r1c5        = <ButtonLocation.r1c5: 5>

### r2c1        = <ButtonLocation.r2c1: 6>

### r2c2        = <ButtonLocation.r2c2: 7>

### r2c3        = <ButtonLocation.r2c3: 8>

### r2c4        = <ButtonLocation.r2c4: 9>

### r2c5        = <ButtonLocation.r2c5: 10>

### r3c1        = <ButtonLocation.r3c1: 11>

### r3c2        = <ButtonLocation.r3c2: 12>

### r3c3        = <ButtonLocation.r3c3: 13>

### r3c4        = <ButtonLocation.r3c4: 14>

### r3c5        = <ButtonLocation.r3c5: 15>

### def         attribute_presentation(self):
Get the string representation of an enum entry. Uses .name when not overridden.

Returns:
    The string representation of an enum entry.

### dock_page2: int
Returns the button location for the second page.
Used as a suffix to the usual button selection: ButtonLocation.r1c1.dock_page2

Returns:
    The value representing the button location for the second page

### @classmethod
Get the button location ID of the row, column specified

Args:
    row: The number of the row starting from the top (1-5)
    col: The number of the column starting from the left (1-3)

Returns:
    The button location ID of the (row, column) location specified


### class     CaptureFlag(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the capture flag values used in the game for units.
Used when placing new objects

Examples

### DEFAULT        = <CaptureFlag.DEFAULT: -1>

### NEVER        = <CaptureFlag.NEVER: 0>

### ONCE        = <CaptureFlag.ONCE: 1>

### MULTIPLE_TIMES        = <CaptureFlag.MULTIPLE_TIMES: 2>

### NEVER_GAIA_AGGRESSIVE        = <CaptureFlag.NEVER_GAIA_AGGRESSIVE: 3>


### class     ChargeEvent(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum provides the integer values used to reference the action which depletes a unit's charge
The meaning of this value depends on Charge Type

Examples

### PERFORM_ATTACK_GROUND_ON_OWN_LOCATION        = <ChargeEvent.PERFORM_ATTACK_GROUND_ON_OWN_LOCATION: -1>

### NO_CHARGE_DEPLETED        = <ChargeEvent.NO_CHARGE_DEPLETED: 0>

### TRANSFORM_AFTER_ATTACK        = <ChargeEvent.NO_CHARGE_DEPLETED: 0>

### CHARGE_DEPLETED_ON_ATTACK        = <ChargeEvent.CHARGE_DEPLETED_ON_ATTACK: 1>


### class     ChargeType(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum provides the integer values used to reference the type of charge that a unit holds

Examples

### SPAWN_BUILDING_ON_TOP_ABILITY        = <ChargeType.SPAWN_BUILDING_ON_TOP_ABILITY: -5>

### CONVERSION_ABILITY        = <ChargeType.CONVERSION_ABILITY: -4>

### AURA_ABILITY        = <ChargeType.AURA_ABILITY: -3>

### TRANSFORM_ABILITY        = <ChargeType.TRANSFORM_ABILITY: -2>

### TEMPORARY_TRANSFORM_ABILITY        = <ChargeType.TEMPORARY_TRANSFORM_ABILITY: -1>

### ATTACK_CHARGE        = <ChargeType.ATTACK_CHARGE: 1>

### UNKNOWN_CHARGE        = <ChargeType.UNKNOWN_CHARGE: 2>

### AREA_ATTACK_CHARGE        = <ChargeType.AREA_ATTACK_CHARGE: 3>

### AGILITY_CHARGE        = <ChargeType.AGILITY_CHARGE: 4>

### IGNORE_MELEE_ATTACK        = <ChargeType.IGNORE_MELEE_ATTACK: 5>

### FIRE_ONLY_CHARGE_PROJECTILES        = <ChargeType.FIRE_ONLY_CHARGE_PROJECTILES: 6>

### FIRE_ONE_CHARGE_AND_ADDITIONAL_SECONDARY_PROJECTILES        = <ChargeType.FIRE_ONE_CHARGE_AND_ADDITIONAL_SECONDARY_PROJECTILES: 7>


### class     ColorMood(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the color mood values used in the game. Used in the
'Change Color Mood' effect

Examples

### DEFAULT        = <ColorMood.DEFAULT: 0>

### AUTUMN        = <ColorMood.AUTUMN: 1>

### WINTER        = <ColorMood.WINTER: 2>

### JUNGLE        = <ColorMood.JUNGLE: 3>

### DESERT        = <ColorMood.DESERT: 4>

### NIGHT        = <ColorMood.NIGHT: 5>

### EVENING        = <ColorMood.EVENING: 6>

### SPRING        = <ColorMood.SPRING: 7>

### SAVANNAH        = <ColorMood.SAVANNAH: 8>

### ARCTIC        = <ColorMood.ARCTIC: 9>

### RAINFOREST        = <ColorMood.RAINFOREST: 10>

### SWAMP        = <ColorMood.SWAMP: 11>

### STEPPES        = <ColorMood.STEPPES: 12>

### MISTY        = <ColorMood.MISTY: 13>

### SUMMER        = <ColorMood.SUMMER: 14>

### MURKY        = <ColorMood.MURKY: 15>

### BRUMOUS        = <ColorMood.BRUMOUS: 16>

### TWILIGHT        = <ColorMood.TWILIGHT: 17>

### DARKNESS        = <ColorMood.DARKNESS: 18>


### class     CombatAbility(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntFlags):
This enum class provides the integer values for the break off combat flags that can be used
in the 'Modify Attribute' effect with the 'Combat Ability' attribute. This is a combinable bit field.

Examples

### NORMAL        = <CombatAbility.NORMAL: 0>

### IGNORE_MELEE_PIERCE_ARMOR        = <CombatAbility.IGNORE_MELEE_PIERCE_ARMOR: 1>

### RESIST_ARMOR_IGNORING_ATTACKS        = <CombatAbility.RESIST_ARMOR_IGNORING_ATTACKS: 2>

### DAMAGE_TARGET_ARMOR        = <CombatAbility.DAMAGE_TARGET_ARMOR: 4>

### ATTACK_GROUND        = <CombatAbility.ATTACK_GROUND: 8>

### BULK_VOLLEY_RELEASE        = <CombatAbility.BULK_VOLLEY_RELEASE: 16>

### ENABLE_AURA_ABILITY        = <CombatAbility.ENABLE_AURA_ABILITY: 32>

### INVERT_AURA_TO_BOOST_SELF        = <CombatAbility.INVERT_AURA_TO_BOOST_SELF: 64>

### ENABLE_STINGERS_ABILITY        = <CombatAbility.ENABLE_STINGERS_ABILITY: 128>


### class     Comparison(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the comparisons in the game. Used in a lot of
conditions like 'Accumulate Attribute' to perform logical operations on the attribute values

Examples

### EQUAL        = <Comparison.EQUAL: 0>

### LESS        = <Comparison.LESS: 1>

### LARGER        = <Comparison.LARGER: 2>

### LESS_OR_EQUAL        = <Comparison.LESS_OR_EQUAL: 3>

### LARGER_OR_EQUAL        = <Comparison.LARGER_OR_EQUAL: 4>

### EQ        = <Comparison.EQUAL: 0>

### LT        = <Comparison.LESS: 1>

### GT        = <Comparison.LARGER: 2>

### LEQ        = <Comparison.LESS_OR_EQUAL: 3>

### GEQ        = <Comparison.LARGER_OR_EQUAL: 4>


### class     DamageClass(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values that represent the damage classes in the game. Used in the 'Chnage
Object Attack/Armour' and 'Modify Attribute' with the 'Attack/Armour' attibutes

Examples

### WONDER        = <DamageClass.WONDER: 0>
Since HD. Only wonders has this armour class. However there is no unit that has this attack class.

### INFANTRY        = <DamageClass.INFANTRY: 1>

### TURTLE_SHIPS        = <DamageClass.TURTLE_SHIPS: 2>

### BASE_PIERCE        = <DamageClass.BASE_PIERCE: 3>

### BASE_MELEE        = <DamageClass.BASE_MELEE: 4>

### WAR_ELEPHANTS        = <DamageClass.WAR_ELEPHANTS: 5>

### UNUSED_ID6        = <DamageClass.UNUSED_ID6: 6>

### UNUSED_ID7        = <DamageClass.UNUSED_ID7: 7>

### CAVALRY        = <DamageClass.CAVALRY: 8>

### UNUSED_ID9        = <DamageClass.UNUSED_ID9: 9>

### UNUSED_ID10        = <DamageClass.UNUSED_ID10: 10>

### ALL_BUILDINGS_EXCEPT_PORT        = <DamageClass.ALL_BUILDINGS_EXCEPT_PORT: 11>
Port is the building with id 446

### UNUSED_ID12        = <DamageClass.UNUSED_ID12: 12>

### STONE_DEFENSE        = <DamageClass.STONE_DEFENSE: 13>

### PREDATOR_ANIMALS_FE        = <DamageClass.PREDATOR_ANIMALS_FE: 14>
Wolf, Bear, Jaguar, Tiger, etc. have this armour class

### ARCHERS        = <DamageClass.ARCHERS: 15>

### BATTLE_SHIPS_AND_SABOTEUR        = <DamageClass.BATTLE_SHIPS_AND_SABOTEUR: 16>
Camels also had this armour class before AK

### RAMS_TREBUCHETS_SIEGE_TOWERS        = <DamageClass.RAMS_TREBUCHETS_SIEGE_TOWERS: 17>

### TREES        = <DamageClass.TREES: 18>

### UNIQUE_UNITS        = <DamageClass.UNIQUE_UNITS: 19>

### SIEGE_WEAPONS        = <DamageClass.SIEGE_WEAPONS: 20>

### STANDARD_BUILDINGS        = <DamageClass.STANDARD_BUILDINGS: 21>

### WALLS_AND_GATES        = <DamageClass.WALLS_AND_GATES: 22>

### GUNPOWDER_UNITS        = <DamageClass.GUNPOWDER_UNITS: 23>

### BOARS        = <DamageClass.BOARS: 24>

### MONKS        = <DamageClass.MONKS: 25>

### CASTLES        = <DamageClass.CASTLES: 26>
Castles, Kreposts, Fortresses, Poenari Castles

### SPEARMEN        = <DamageClass.SPEARMEN: 27>

### CAVALRY_ARCHERS        = <DamageClass.CAVALRY_ARCHERS: 28>

### EAGLE_WARRIORS        = <DamageClass.EAGLE_WARRIORS: 29>

### CAMELS        = <DamageClass.CAMELS: 30>
Camels use this armour class since and after AK

### LEITIS_ATTACK        = <DamageClass.LEITIS_ATTACK: 31>
Armor class remains on units but leitis no longer uses it for attacks

### CONDOTTIERI        = <DamageClass.CONDOTTIERI: 32>

### PROJECTILE_GUNPOWDER_SECONDARY        = <DamageClass.PROJECTILE_GUNPOWDER_SECONDARY: 33>

### FISHING_SHIPS        = <DamageClass.FISHING_SHIPS: 34>

### MAMELUKES        = <DamageClass.MAMELUKES: 35>

### HEROES_AND_KINGS        = <DamageClass.HEROES_AND_KINGS: 36>

### HUSSITE_WAGONS        = <DamageClass.HUSSITE_WAGONS: 37>

### UNUSED_ID38        = <DamageClass.UNUSED_ID38: 38>
Skirmishers has this armor class

### UNUSED_ID39        = <DamageClass.UNUSED_ID39: 39>
Camels and shotel warriors has this armor class

### UNUSED_ID40        = <DamageClass.UNUSED_ID40: 40>

### UNUSED_ID41        = <DamageClass.UNUSED_ID41: 41>

### UNUSED_ID42        = <DamageClass.UNUSED_ID42: 42>

### UNUSED_ID43        = <DamageClass.UNUSED_ID43: 43>

### UNUSED_ID44        = <DamageClass.UNUSED_ID44: 44>

### UNUSED_ID45        = <DamageClass.UNUSED_ID45: 45>

### UNUSED_ID46        = <DamageClass.UNUSED_ID46: 46>

### UNUSED_ID47        = <DamageClass.UNUSED_ID47: 47>

### UNUSED_ID48        = <DamageClass.UNUSED_ID48: 48>

### UNUSED_ID49        = <DamageClass.UNUSED_ID49: 49>


### class     DecisionOption(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values for the Decision Triggered Condition.

Examples:

### Option1        = <DecisionOption.Option1: 1>

### Option2        = <DecisionOption.Option2: 2>


### class     DifficultyLevel(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference difficulty level of the game. Used in the 'Difficulty
Level' condition.

Examples

### EASIEST        = <DifficultyLevel.EASIEST: 4>

### STANDARD        = <DifficultyLevel.STANDARD: 3>

### MODERATE        = <DifficultyLevel.MODERATE: 2>

### HARD        = <DifficultyLevel.HARD: 1>

### HARDEST        = <DifficultyLevel.HARDEST: 0>

### EXTREME        = <DifficultyLevel.EXTREME: -1>
The only exception in the entire scenario where the value -1 is NOT an unselected/invalid value.
This might cause issues in the parser, please report them if you find any.


### class     DiplomacyState(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the diplomacy states in the game. Used in the 'Change
Diplomacy' effect and the 'Diplomacy State' condition

Examples

### ALLY        = <DiplomacyState.ALLY: 0>

### NEUTRAL        = <DiplomacyState.NEUTRAL: 1>

### ENEMY        = <DiplomacyState.ENEMY: 3>


### class     DisableUnitFlag(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the disable unit flag values used in the game. Used in the
'Modify Attribute' effect with the 'Disable Unit Flag' attributes

Examples

### DISABLED        = <DisableUnitFlag.DISABLED: 1>

### LIMITED_TRAINING_CAN_NOT_BE_RETRAINED        = <DisableUnitFlag.LIMITED_TRAINING_CAN_NOT_BE_RETRAINED: 2>

### LIMITED_TRAINING_CAN_BE_RETRAINED        = <DisableUnitFlag.LIMITED_TRAINING_CAN_BE_RETRAINED: 4>


### class     FogVisibility(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to references the different fog visibility settings that can be
used in the 'Modify Attribute' effect with the 'Fog Visibility' attribute.

Examples

### NOT_VISIBLE        = <FogVisibility.NOT_VISIBLE: 0>

### ALWAYS_VISIBLE        = <FogVisibility.ALWAYS_VISIBLE: 1>

### VISIBLE_IF_ALIVE        = <FogVisibility.VISIBLE_IF_ALIVE: 2>

### INVERTED_VISIBILITY        = <FogVisibility.INVERTED_VISIBILITY: 3>

### CHECK_DOPPELGANGER        = <FogVisibility.CHECK_DOPPELGANGER: 4>


### class     GarrisonType(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntFlags):
This enum class provides the integer values for the different garrison type flags that can be used in the 'Modify
Attribute' effect with the 'Garrison Type' attribute. This is a combinable bit field

Examples

### NONE        = <GarrisonType.NONE: 0>

### VILLAGERS        = <GarrisonType.VILLAGERS: 1>

### INFANTRY        = <GarrisonType.INFANTRY: 2>

### CAVALRY        = <GarrisonType.CAVALRY: 4>

### MONKS        = <GarrisonType.MONKS: 8>

### HERDABLES        = <GarrisonType.HERDABLES: 16>

### SIEGE        = <GarrisonType.SIEGE: 32>

### SHIPS        = <GarrisonType.SHIPS: 64>


### class     HeroStatusFlag(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntFlags):
This enum class provides the integer values for the different hero status flags that can be used in the 'Modify
Attribute' effect with the 'Hero Status' attribute. This is a combinable bit field

Methods

- HeroStatusFlag.combine()

- HeroStatusFlag.split_flags()

Examples

### @staticmethod
This method combines the given hero status flags into an integer value

Args:
    full_hero_status: Enabling this for a unit grants all the flags mentioned below except invert_all_flags
    cannot_be_converted: Enabling this for a unit makes it un-convertable
    hero_regeneration: Enabling this for a unit grants 0.5 HP/s heal rate to the unit
    defensive_stance_by_default: Enabling this for a unit makes it be on defensive stance by default
    protected_formation: Enabling this for a unit makes it be in protected formation by default
    delete_confirmation: Enabling this for a unit will bring up a delete confirmation for the unit when trying
        to delete it IF the player has them enabled
    hero_glow: Enabling this for a unit grants it the golden hero glow effect
    invert_all_flags: Enabling this for a unit will invert all the above flags except full_hero_status

Returns:
    An integer combining all the different hero status flags into one value

### @staticmethod
Split the Hero Status flags into boolean variables related to their effects

Args:
    value: An integer value representing all the hero status flags set

Returns:
    A dict with all the flags values as keys and a bool as their value

### NO_HERO_STATUS        = <HeroStatusFlag.NO_HERO_STATUS: 0>

### FULL_HERO_STATUS        = <HeroStatusFlag.FULL_HERO_STATUS: 1>

### CANNOT_BE_CONVERTED        = <HeroStatusFlag.CANNOT_BE_CONVERTED: 2>

### HERO_REGENERATION        = <HeroStatusFlag.HERO_REGENERATION: 4>

### DEFENSIVE_STANCE_BY_DEFAULT        = <HeroStatusFlag.DEFENSIVE_STANCE_BY_DEFAULT: 8>

### PROTECTED_FORMATION        = <HeroStatusFlag.PROTECTED_FORMATION: 16>

### DELETE_CONFIRMATION        = <HeroStatusFlag.DELETE_CONFIRMATION: 32>

### HERO_GLOW        = <HeroStatusFlag.HERO_GLOW: 64>

### INVERT_FLAGS        = <HeroStatusFlag.INVERT_FLAGS: 128>


### class     Hotkey(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the blast level values used in the game. Used in the
'Modify Attribute' effect with the 'HotKey ID' attribute

Many hotkeys are missing from this file (Like arrow up). The reason for this is explained in the UGC guide:
https://divy1211.github.io/AoE2DE_UGC_Guide/general/hotkeys/hotkeys/

Examples

### SPACE        = <Hotkey.SPACE: 10101>

### PAGE_UP        = <Hotkey.PAGE_UP: 15000>

### LEFT_ARROW        = <Hotkey.LEFT_ARROW: 2312>

### RIGHT_ARROW        = <Hotkey.RIGHT_ARROW: 19707>

### DOWN_ARROW        = <Hotkey.DOWN_ARROW: 19731>

### INSERT        = <Hotkey.INSERT: 9025>

### DELETE        = <Hotkey.DELETE: 19602>

### ZERO        = <Hotkey.ZERO: 99>

### ONE        = <Hotkey.ONE: 98>

### TWO        = <Hotkey.TWO: 10360>

### THREE        = <Hotkey.THREE: 9786>

### FOUR        = <Hotkey.FOUR: 10362>

### FIVE        = <Hotkey.FIVE: 9785>

### SIX        = <Hotkey.SIX: 213>

### SEVEN        = <Hotkey.SEVEN: 8828>

### EIGHT        = <Hotkey.EIGHT: 9448>

### NINE        = <Hotkey.NINE: 9783>

### A        = <Hotkey.A: 1001>

### B        = <Hotkey.B: 1005>

### C        = <Hotkey.C: 1201>

### D        = <Hotkey.D: 1151>

### E        = <Hotkey.E: 1007>

### F        = <Hotkey.F: 4137>

### G        = <Hotkey.G: 2012>

### H        = <Hotkey.H: 2407>

### I        = <Hotkey.I: 1212>

### J        = <Hotkey.J: 1222>

### K        = <Hotkey.K: 4141>

### L        = <Hotkey.L: 1101>

### M        = <Hotkey.M: 1006>

### N        = <Hotkey.N: 3001>

### O        = <Hotkey.O: 214>

### P        = <Hotkey.P: 1210>

### Q        = <Hotkey.Q: 4169>

### R        = <Hotkey.R: 1200>

### S        = <Hotkey.S: 1102>

### T        = <Hotkey.T: 2016>

### U        = <Hotkey.U: 1205>

### V        = <Hotkey.V: 1150>

### W        = <Hotkey.W: 1008>

### X        = <Hotkey.X: 1002>

### Y        = <Hotkey.Y: 2008>

### Z        = <Hotkey.Z: 4174>

### APPLICATION        = <Hotkey.APPLICATION: 19704>

### NUM_ZERO        = <Hotkey.NUM_ZERO: 19721>

### NUM_ONE        = <Hotkey.NUM_ONE: 4563>

### NUM_FOUR        = <Hotkey.NUM_FOUR: 19499>

### NUM_FIVE        = <Hotkey.NUM_FIVE: 5558>

### NUM_SEVEN        = <Hotkey.NUM_SEVEN: 10069>

### NUM_EIGHT        = <Hotkey.NUM_EIGHT: 1011>

### NUM_DELETE        = <Hotkey.NUM_DELETE: 20123>

### F3        = <Hotkey.F3: 9798>

### F4        = <Hotkey.F4: 22019>

### F7        = <Hotkey.F7: 9840>

### F8        = <Hotkey.F8: 1152>

### F15        = <Hotkey.F15: 10661>


### class     LocalTechnology(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference local technologies of the game.
Used in the 'Research Local Technologies' effect and 'Local Technology Researched' condition.

It indirectly uses the TechInfo enum class as that's where the values are stored. This is a narrow selection
created for convienience.

Examples

### DEFENSIVE_TOWN_CENTER        = <LocalTechnology.DEFENSIVE_TOWN_CENTER: 1197>

### ECONOMIC_TOWN_CENTER        = <LocalTechnology.ECONOMIC_TOWN_CENTER: 1195>

### MILITARY_TOWN_CENTER        = <LocalTechnology.MILITARY_TOWN_CENTER: 1196>

### FORTIFIED_OUTPOST        = <LocalTechnology.FORTIFIED_OUTPOST: 1270>

### DEFENSIVE_EMPLACEMENT        = <LocalTechnology.DEFENSIVE_EMPLACEMENT: 1323>

### OFFENSIVE_EMPLACEMENT        = <LocalTechnology.OFFENSIVE_EMPLACEMENT: 1324>


### class     ObjectAttribute(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference all the different object attributes in the game. Used
in the 'Modify Attribute' effect to control which attribute of an object is modified.

Examples

### HIT_POINTS        = <ObjectAttribute.HIT_POINTS: 0>
This attribute refers to the health of the units

### LINE_OF_SIGHT        = <ObjectAttribute.LINE_OF_SIGHT: 1>
This is the distance a unit can see around itself

### GARRISON_CAPACITY        = <ObjectAttribute.GARRISON_CAPACITY: 2>
This is the amount of units that can garrison inside another unit

### UNIT_SIZE_X        = <ObjectAttribute.UNIT_SIZE_X: 3>
This determines the x-size of the unit's collision hitbox (width of the unit)

### UNIT_SIZE_Y        = <ObjectAttribute.UNIT_SIZE_Y: 4>
This determines the y-size of the unit's collision hitbox (length of the unit)

### MOVEMENT_SPEED        = <ObjectAttribute.MOVEMENT_SPEED: 5>
This is the movement speed of a unit, measured in tiles per second

### ROTATION_SPEED        = <ObjectAttribute.ROTATION_SPEED: 6>
This is the rate at which units can rotate, measured in seconds per frame (this many seconds must pass before the object can switch to the next rotation frame). For example, for a trebuchet to start attacking a building facing the opposite direction, it has to rotate to face that way first

### ARMOR        = <ObjectAttribute.ARMOR: 8>
This is the quantity of armour a unit has on any of its Armour Classes. If you do not know what an Armour Class is, refer to the Damage Calculation section of this guide. Note that changing the armour through this option will show it as being added to the base armour amount. (for example: 4+4)

### ATTACK        = <ObjectAttribute.ATTACK: 9>
This is the quantity of attack a unit has on any of its Attack Classes. If you do not know what an Attack Class is, refer to the Damage Calculation section of this guide. Note that changing the attack through this option will show it as being added to the base attack amount. (for example: 6+2)

### ATTACK_RELOAD_TIME        = <ObjectAttribute.ATTACK_RELOAD_TIME: 10>
This is the minimum time that must pass before a unit is able to fire another shot. For melee units it is the minimum time between two successive hits that they can do

### ACCURACY_PERCENT        = <ObjectAttribute.ACCURACY_PERCENT: 11>
This determines how accurately a unit can aim at another unit

- Notes:

This accuracy is the accuracy of a unit to fire at the exact centre of its target. If the shot fired is not aimed at the exact centre of the target, it may still hit the target if its not off by too much since it can still land within the hitbox of the target, just not at the exact centre
Thus, bigger targets are actually easier to hit, which explains why buildings are an easier target to hit for trebuchets than small units

In this image, you can see that shots that were fired in the red area in the 2nd scenario would've hit if the target had been closer like in the first scenario, but since the target is far away, they actually miss
More technically, the visual angle of an object of the same size that is farther away is smaller, thus giving a smaller room for error for the shot in terms of the range of angles that will make the shot hit
The chance of a unit getting converted by a monk is also determined by its accuracy
If you modify an onager to have a big blast radius and give it a small accuracy, then attack a lot of units bunched together, the accuracy determines what percentage of units take damage from the blast of the onager! This is the reason why warwolf trebuchets get 100% accuracy because otherwise the blast wouldn't damage all of the units. Another interesting consequence of this is the delete trick with onagers and mangonels. This is where a mangonel is deleted immediately after it fires its shot and because a dead unit doesn't have an accuracy, it defaults to 100% and thus deals more damage to all the units in the blast radius
Note: There are two other factors that play a role in determining the damage from the shot fired by the deleted mangonel

- The damage from a mangonel's shot is decreased over distance when moving outward from the centre of the blast (the targeted point). However, when the mangonel is deleted, this decrease over distance doesn't happen, and the projectile deals the full 100% damage to all the units in the blast radius!

- A shot that is fired from lower elevation would normally deal only 75% of its normal damage due to the elevation damage reduction. deleting a mangonel in this case also makes the damage the full 100% as if there was no elevation difference

### MAXIMUM_RANGE        = <ObjectAttribute.MAXIMUM_RANGE: 12>
This is the maximum range of a unit. Note that to be able to shoot at a target, it must be visible to the unit via its own line of sight or from another unit's line of sight

### WORK_RATE        = <ObjectAttribute.WORK_RATE: 13>
This is the work rate for any unit that can do work. Villagers, Fishing Ships, Serjeants

### CARRY_CAPACITY        = <ObjectAttribute.CARRY_CAPACITY: 14>
This is the carry capacity of Villagers

### BASE_ARMOR        = <ObjectAttribute.BASE_ARMOR: 15>
This is the quantity of base armour a unit has on any of its Armour Classes. If you do not know what an Armour Class is, refer to the Damage Calculation section of this guide. Note that changing the armour through this option will show it as the base armour itself, and it will not be added to the regular amount

### PROJECTILE_UNIT        = <ObjectAttribute.PROJECTILE_UNIT: 16>
This is the ID of the projectile that a unit fires

### BUILDING_ICON_OVERRIDE        = <ObjectAttribute.BUILDING_ICON_OVERRIDE: 17>
The functionality of this attribute is unknown as it doesn't always behave certainly. If you know what this attribute does, please let the authors of this guide know!

### TERRAIN_DEFENSE_BONUS        = <ObjectAttribute.TERRAIN_DEFENSE_BONUS: 18>
Unknown... What does this attribute do?

### PROJECTILE_SMART_MODE        = <ObjectAttribute.PROJECTILE_SMART_MODE: 19>
This is a combinable bit field. Controls the following two behaviours for projectiles:

- Flags:

- 0: No Ballistics

- 1: Has Ballistics

- 2: Deals full damage on missed hit

- Notes:

For example, if we set this property of the projectile used by an archer to 1, it will have ballistics. (This is exactly what researching ballistics does in the first place). If we set this property to 2, a missed projectile that hits another unit will deal its full damage instead of the 50% that it would normally do
What if we want to enable both properties at once? This is achieved by adding the flag values for both of them together. Setting this property to 3 enables both effects

### MINIMUM_RANGE        = <ObjectAttribute.MINIMUM_RANGE: 20>
The minimum distance a unit must be from an attacking unit for the attacking unit to be able to fire its projectile

### AMOUNT_OF_1ST_RESOURCE_STORAGE        = <ObjectAttribute.AMOUNT_OF_1ST_RESOURCE_STORAGE: 21>
This is the amount of 1st resource contained in any unit. Refer to A.G.E. to see which resource this is for each unit

### BLAST_WIDTH        = <ObjectAttribute.BLAST_WIDTH: 22>
All enemy units inside this radius take damage from an attacking unit. This is used by elephants, Druzhina Halberdiers, and Logistica Cataphracts

### SEARCH_RADIUS        = <ObjectAttribute.SEARCH_RADIUS: 23>
The maximum distance at which a unit can detect and auto attack enemy units

### BONUS_DAMAGE_RESISTANCE        = <ObjectAttribute.BONUS_DAMAGE_RESISTANCE: 24>
Used by Sicilians for the 33% bonus damage resistance. Set to 0.33 for all Sicilian land military units except siege

- Notes:

Do not make it greater than 1

### ICON_ID        = <ObjectAttribute.ICON_ID: 25>
The ID of the icon that you want a unit to show

### AMOUNT_OF_2ND_RESOURCE_STORAGE        = <ObjectAttribute.AMOUNT_OF_2ND_RESOURCE_STORAGE: 26>
This is the amount of 2nd resource contained in any unit. Refer to A.G.E. to see which resource this is for each unit

### AMOUNT_OF_3RD_RESOURCE_STORAGE        = <ObjectAttribute.AMOUNT_OF_3RD_RESOURCE_STORAGE: 27>
This is the amount of 3rd resource contained in any unit. Refer to A.G.E. to see which resource this is for each unit

### FOG_VISIBILITY        = <ObjectAttribute.FOG_VISIBILITY: 28>
Controls visibility of a unit through the fog of war

- Flags:

- 0: Not Visible

- 1: Always Visible

- 2: Visible If Alive

- 3: Inverted Visibility

- 4: Check Doppelganger

### OCCLUSION_MODE        = <ObjectAttribute.OCCLUSION_MODE: 29>
This is a combinable bit field. Controls the outlines of units as seen through other units

- Flags:

- 0: No outline

- 1: Display outline when behind other units that have flag 2

- 2: Other units' outlines are rendered when they are behind this unit

- 4: Display outline on this unit's foundation when behind other units that have flag 2

### GARRISON_TYPE        = <ObjectAttribute.GARRISON_TYPE: 30>
This is a combinable bit field. Controls which units are able to garrison in a building. A unit needs to have the garrison in building task to be able to garrison in a building to begin with

- Flags:

- 1: Villagers

- 2: Infantry

- 4: Cavalry

- 8: Monks

- 16: Herdables

- 32: Siege

- 64: Ships

### UNIT_SIZE_Z        = <ObjectAttribute.UNIT_SIZE_Z: 32>
This determines the z-size of the unit's collision hitbox (height of the unit)

- Notes:

Setting this to 0 allows other units to walk over this unit
Does this still control the HP bar location as specified in A.G.E.?

### CAN_BE_BUILT_ON        = <ObjectAttribute.CAN_BE_BUILT_ON: 33>
Determines if a building foundation can be placed on top of a unit

- Flags:

- 0: Disallow unit to be built on. This is the value for almost all units

- 1: Allow unit to be built on. This is the value for corpses, rubble, eye candy

### FOUNDATION_TERRAIN        = <ObjectAttribute.FOUNDATION_TERRAIN: 34>
This is the ID of the terrain created under a building when its construction is finished

- Flags:

- -1: No terrain change

- Notes:

Only affects units of Type 80 (Building)

### HERO_STATUS        = <ObjectAttribute.HERO_STATUS: 40>
This is a combinable bit field. Controls the following properties:

- Flags:

- 1: Full Hero Status

- 2: Cannot be Converted

- 4: Self Regeneration (30 HP/min)

- 8: Defensive Stance by Default

- 16: Protected Formation by Default

- 32: Safe Delete Confirmation

- 64: Hero Glow

- 128: Invert All Flags (except flag 1)

- Notes:

For example, if we set the hero status of a knight to 2, a monk will not be able to convert it. If we set the hero status of a militia to 4, it will regenerate HP automatically
What if we want to enable multiple properties at once? This is achieved by adding the flag values for those properties together and setting the hero status to that value. For example, if we want to make a paladin both unconvertable and regenerate HP automatically, we can set its hero status to 2+4 = 6. This means that the hero status of a unit can take on any values in the range 1-63. If you set it to any other value, it does not have any effect on the unit
This works because notice that there is one and only one way to add different flag values together to obtain a particular value for the hero status! For example, if we have a value of 20 for the hero status of a unit, the only way to make 20 from the above flag values is to add 4 and 16. Thus, we know that the properties corresponding to the flag values 4 (self regeneration) and 16 (protected formation by default) must be enabled for that unit
This is a consequence of the fact that every number can be represented as a unique sum of powers of two (binary numbers)

### FRAME_DELAY        = <ObjectAttribute.FRAME_DELAY: 41>
The amount of delay between the point when the attacking animation starts and the actual hit happening for military units. This is what makes Cavalry Archers annoying to micro

### TRAIN_LOCATION        = <ObjectAttribute.TRAIN_LOCATION: 42>
The ID of the unit that trains any given unit. Barracks train Militia, so the train location of a Militia is the ID of the Barracks

### TRAIN_BUTTON        = <ObjectAttribute.TRAIN_BUTTON: 43>
The button used for training any given unit. For example, Militia are trained by using the first button, hence the Button Location of Militia is 1. This number ranges from 0-15

### BLAST_ATTACK_LEVEL        = <ObjectAttribute.BLAST_ATTACK_LEVEL: 44>
A unit deals blast damage to other units with equal or higher Blast Defense Level that are in its blast radius. For example, while mangonels (blast attack: 2) can damage your own units (blast defense of all player owned units is always 2), scorpions (blast attack: 3) cannot do the same

- Flags:

- 0: Damage resources, nearby allied units and tress

- 1: Damage trees, nearby allied units

- 2: Damage nearby and allied units

- 3: Damage targeted unit only

- 4: Damage enemy units only

- 8: Ignore friendly fire

- 16: Unused

- 32: Unused

- 64: Attenuate damage as distance from the centre of attack increases (infantry only)

- 128: Blast damage is dealt along the direction the unit is facing only. This area is a very narrow cone

- Notes:

One of the flags 0-3 can be combined with the combinable flags 4 to 128 by adding the two values

### BLAST_DEFENSE_LEVEL        = <ObjectAttribute.BLAST_DEFENSE_LEVEL: 45>
A unit feels the blast damage from other units with equal or lower Blast Attack Level and if it is inside the attacker's blast radius. For example, while onagers (blast attack: 1) can cut trees (blast defense 1), mangonels (blast attack: 2) cannot do the same

- Flags:

- 0: damage resources, nearby allied units and tress

- 1: damage trees, nearby allied units

- 2: damage nearby allied units

- 3: damage targeted unit only

### SHOWN_ATTACK        = <ObjectAttribute.SHOWN_ATTACK: 46>
The amount of attack that is displayed as a unit's attack (may not actually be the true attack)

### SHOWN_RANGE        = <ObjectAttribute.SHOWN_RANGE: 47>
The quantity that is displayed as a unit's attack ingame (may not actually be the true attack)

### SHOWN_MELEE_ARMOR        = <ObjectAttribute.SHOWN_MELEE_ARMOR: 48>
The quantity that is displayed as a unit's melee armour ingame (may not actually be the true armour)

### SHOWN_PIERCE_ARMOR        = <ObjectAttribute.SHOWN_PIERCE_ARMOR: 49>
The quantity that is displayed as a unit's pierce armour ingame (may not actually be the true armour)

### OBJECT_NAME_ID        = <ObjectAttribute.OBJECT_NAME_ID: 50>
The string ID to use for the name of an object. A string ID is used for refering to strings that the game recognises by default. It can be used to automatically set names by using a value that the game recognises. Trying out the value 1 on a unit and seeing what happens is left as an excersise for the reader

### SHORT_DESCRIPTION_ID        = <ObjectAttribute.SHORT_DESCRIPTION_ID: 51>
The string ID for the Short Description of an object. A string ID is used for refering to strings that the game recognises by default. It can be used to automatically set a Short Description by using a value that the game recognises. Trying out the value 1 on a unit and seeing what happens is left as an excersise for the reader

### TERRAIN_RESTRICTION_ID        = <ObjectAttribute.TERRAIN_RESTRICTION_ID: 53>
This number determines how a unit interacts with terrains and which terrains it can walk on

- Flags:

- 0: All

- 1: Land And Shallows

- 2: Beach

- 3: Water Small Trail

- 4: Land

- 5: Nothing

- 6: Water No Trail

- 7: All Except Water

- 8: Land Except Farm

- 9: Nothing 2

- 10: Land And Beach

- 11: Land Except Farm 2

- 12: All Except Water Bridge Cannon

- 13: Water Medium Trail

- 14: All Except Water Bridge Arrow

- 15: Water Large Trail

- 16: Grass And Beach

- 17: Water And Bridge Except Beach

- 18: All Except Water Bridge Spear

- 19: Only Water And Ice

- 20: All Except Water Wheel

- 21: Shallow Water

- 22: All Dart

- 23: All Arrow Fire

- 24: All Cannon Fire

- 25: All Spear Fire

- 26: All Dart Fire

- 27: All Laser

- 28: All Except Water Cavalry

- 29: All Except Water Packet Trebuchet

- 30: Water Smallest Trail

### UNIT_TRAIT        = <ObjectAttribute.UNIT_TRAIT: 54>
This is a combinable bit field. Controls the following properties:

- Flags:

- 1: Garrison Unit

- 2: Ship Unit

- 4: Build Another Building (Serjeants) [See Special Ability: Mode 7]

- 8: Transform Into Another Unit (Ratha)

- 16: Auto Scout Unit

- Notes:

See Also:

Trait Piece

### TRAIT_PIECE        = <ObjectAttribute.TRAIT_PIECE: 56>
This can be set to the ID of a unit that is used along with some of the Unit Traits

- Flags:

- 1: Unused

- 2: Unused

- 4: Build Unit

- 8: Transform Unit

- 16: Unused

- Notes:

See Also:

Unit Trait

### DEAD_UNIT_ID        = <ObjectAttribute.DEAD_UNIT_ID: 57>
This is the ID of the unit to spawn after the current unit dies. This is whats used to make the dismounted konniks possible

### HOTKEY_ID        = <ObjectAttribute.HOTKEY_ID: 58>
This number determines which hotkey is assigned to a unit

### MAXIMUM_CHARGE        = <ObjectAttribute.MAXIMUM_CHARGE: 59>
The maximum amount of charge that a unit can hold

### RECHARGE_RATE        = <ObjectAttribute.RECHARGE_RATE: 60>
The rate of charge regeneration per second

### CHARGE_EVENT        = <ObjectAttribute.CHARGE_EVENT: 61>
This action depletes the unit's charge

- Flags:

- Charge Type one of 1, 2, or 3: 1 - Deplete charge, 0 - Keep charge

- Charge Type one of 6, or 7: Max range modifier

- Charge Type is -1: 0 - Transform unit until one attack, -1 - perform attack ground on it's location

- Charge Type is -2: 0 - Transform unit until one attack

- Charge Type is -3: Aura task duration

- Charge Type is -4: Conversion range (maybe overridden by conversion tasks)

### CHARGE_TYPE        = <ObjectAttribute.CHARGE_TYPE: 62>
The type of charge that a unit holds

- Flags:

- -5: Spawn Building on top of the unit (Uses unit set in Trait Piece)

- -4: Conversion ability (Needs task 104). Charge Target defines the conversion percent chance

- -3: Active aura ability (Needs task 155 with unused flag 8 set)

- -2: Active targetted transform (Uses unit set in Trait Piece). If charge target = -1, use attack ground targetting

- -1: Active temporary transform (Uses unit set in Trait Piece)

- 1: Attack charge

- 2: ??? charge

- 3: Area attack charge

- 4: Agility charge

- 5: Ignore Melee Attack

- 6: Fire only Charge projectiles, sets Total Projectiles to the value of Max Total Projectiles (Lou Chuan)

- 7: Fires 1 Charge projectile and additional Secondary Projectiles, sets Total Projectiles to the value of Max Total Projectiles

### COMBAT_ABILITY        = <ObjectAttribute.COMBAT_ABILITY: 63>
Combinable bit field. Controls several attacking behaviours for units

- Flags:

- 1: Ignore melee and pierce armours of the targeted unit

- 2: Resist armour-ignoring attacks

- 4: Damage the targeted unit's melee and pierce armors by 1, for a minimum of 0 (Obuch)

- 8: Attack ground ability

- 16: Bulk volley release (kipchak/siege weapons)

- 32: Enable aura ability (task 155) (Stronghold castle/Caravanserai/Centurion)

- 64: Invert aura ability (task 155) to boost self (Monaspa) - Auto Search = 1 needed for multiple tasks

- 128: Activate stringer ability (task 157)

### ATTACK_DISPERSION        = <ObjectAttribute.ATTACK_DISPERSION: 64>
Half of the radius from the target unit in which missed projectiles fired by this unit can land in

### SECONDARY_PROJECTILE_UNIT        = <ObjectAttribute.SECONDARY_PROJECTILE_UNIT: 65>
This is the ID of the secondary projectile that a unit fires (Chu Ko Nu)

### BLOOD_UNIT        = <ObjectAttribute.BLOOD_UNIT: 66>
This is the ID of a secondary unit to spawn after the current unit dies. This could potentially be used along with dead unit ID to spawn two units after a single unit dies

### PROJECTILE_HIT_MODE        = <ObjectAttribute.PROJECTILE_HIT_MODE: 67>
Controls how a projectile collides with units in the path of its target. Currently changing this through XS has no effect

- Flags:

- 0: Collide only with the targeted unit

- 1: Collide with any damage-able units in the path to the targetted unit

- 2: Collide with any unit in the path to the targetted unit

### PROJECTILE_VANISH_MODE        = <ObjectAttribute.PROJECTILE_VANISH_MODE: 68>
Controls if a projectile passes through or disappears on impact. Currently changing this through XS has no effect

- Flags:

- 0: Disappear on first impact

- 1: Pass through

- 2: Always spawn a dead unit

### PROJECTILE_ARC        = <ObjectAttribute.PROJECTILE_ARC: 69>
Controls the maximum height of the fired projectile

### ATTACK_GRAPHIC        = <ObjectAttribute.ATTACK_GRAPHIC: 70>
Controls the Attack Graphic

### STANDING_GRAPHIC        = <ObjectAttribute.STANDING_GRAPHIC: 71>
The sprite animation shown when a unit is idle

- Notes:

Units randomly choose between this or Standing Graphic 2

### STANDING_GRAPHIC_2        = <ObjectAttribute.STANDING_GRAPHIC_2: 72>
The sprite animation shown when a unit is idle

- Notes:

Units randomly choose between this or Standing Graphic

### DYING_GRAPHIC        = <ObjectAttribute.DYING_GRAPHIC: 73>
The sprite animation shown when a unit dies

### UNDEAD_GRAPHIC        = <ObjectAttribute.UNDEAD_GRAPHIC: 74>
This graphic is shown after a unit's dying animation instead of replacing it with its dead unit if its "Undead Mode" is set to 1. Used to assign decay graphic to units without "Undead Mode" set to 1. Overrides the standing graphic of the object's dead unit

- Notes:

Depends on Undead Mode flag

### WALKING_GRAPHIC        = <ObjectAttribute.WALKING_GRAPHIC: 75>
The sprite animation shown when a unit is walking

### RUNNING_GRAPHIC        = <ObjectAttribute.RUNNING_GRAPHIC: 76>
The sprite animation shown when a unit is running

- Notes:

A unit runs when it is issued an attack command, or when a unit is fleeing (deer-like units)
Most units do not have a running graphic
A graphic can multiply the speed of the unit it is applied to
This is used for deer, wolves, boars, etc. when they are issued an attack command

### SPECIAL_GRAPHIC        = <ObjectAttribute.SPECIAL_GRAPHIC: 77>
This sprite animation is shown  when a unit uses one of "Block", "Charge", or "Counter Charge" special abilities

- Notes:

Special abilities are an unused feature in AoE2, they were planned but never made it into AoK

### OBSTRUCTION_TYPE        = <ObjectAttribute.OBSTRUCTION_TYPE: 78>
Controls unit outline and collision

- Flags:

- 0: Square outline, and passable

- 1: Same as 0

- 2: Solid square outline, and has collision box

- 3: Square outline, and has collision box

- 4: No outline, and passable

- 5: Round outline, and has collision box

- 10: Same as 2, but designed for mountains

- 11: Consider the selection size of a radius entirely as opposed to the actual defined collision size

- 12: Ignore hard obstructions entirely and just consider the space occupied with no obstruction at all

- 13: Consider the selection radius when placing other objects, but use the original obstruction size for hard obstructions

### BLOCKAGE_CLASS        = <ObjectAttribute.BLOCKAGE_CLASS: 79>
Controls unit blockage class

- Flags:

- 0: Forces default obstruction type

- 1: Resource

- 2: Unit

- 3: Building

- 4: Wall

- 5: Gate, allows trespassing

- 6: Cliff, blocks walling

### SELECTION_EFFECT        = <ObjectAttribute.SELECTION_EFFECT: 80>
Controls unit hit point bar and outline

- Flags:

- 0: Has hit point bar

- 1: Has hit point bar, and outline

- 2: No hit point bar, or outline

- 3: No hit point bar, but has outline

### SPECIAL_ABILITY        = <ObjectAttribute.SPECIAL_ABILITY: 81>
Enables certain special abilities

- Flags:

- 3: Enable charge attack ability (task 133)

### IDLE_ATTACK_GRAPHIC        = <ObjectAttribute.IDLE_ATTACK_GRAPHIC: 82>
TODO

### HERO_GLOW_GRAPHIC        = <ObjectAttribute.HERO_GLOW_GRAPHIC: 83>
TODO

### GARRISON_GRAPHIC        = <ObjectAttribute.GARRISON_GRAPHIC: 84>
TODO

### CONSTRUCTION_GRAPHIC        = <ObjectAttribute.CONSTRUCTION_GRAPHIC: 85>
TODO

### SNOW_GRAPHIC        = <ObjectAttribute.SNOW_GRAPHIC: 86>
TODO

### DESTRUCTION_GRAPHIC        = <ObjectAttribute.DESTRUCTION_GRAPHIC: 87>
TODO

### DESTRUCTION_RUBBLE_GRAPHIC        = <ObjectAttribute.DESTRUCTION_RUBBLE_GRAPHIC: 88>
TODO

### RESEARCHING_GRAPHIC        = <ObjectAttribute.RESEARCHING_GRAPHIC: 89>
TODO

### RESEARCH_COMPLETED_GRAPHIC        = <ObjectAttribute.RESEARCH_COMPLETED_GRAPHIC: 90>
TODO

### DAMAGE_GRAPHIC        = <ObjectAttribute.DAMAGE_GRAPHIC: 91>
TODO

### SELECTION_SOUND        = <ObjectAttribute.SELECTION_SOUND: 92>
TODO

### SELECTION_SOUND_EVENT        = <ObjectAttribute.SELECTION_SOUND_EVENT: 93>
TODO

### DYING_SOUND        = <ObjectAttribute.DYING_SOUND: 94>
TODO

### DYING_SOUND_EVENT        = <ObjectAttribute.DYING_SOUND_EVENT: 95>
TODO

### TRAIN_SOUND        = <ObjectAttribute.TRAIN_SOUND: 96>
TODO

### TRAIN_SOUND_EVENT        = <ObjectAttribute.TRAIN_SOUND_EVENT: 97>
TODO

### DAMAGE_SOUND        = <ObjectAttribute.DAMAGE_SOUND: 98>
TODO

### DAMAGE_SOUND_EVENT        = <ObjectAttribute.DAMAGE_SOUND_EVENT: 99>
TODO

### RESOURCE_COSTS        = <ObjectAttribute.RESOURCE_COSTS: 100>
Refers to the first resource cost of a unit. Refer to A.G.E. to see which resource cost that is

### TRAIN_TIME        = <ObjectAttribute.TRAIN_TIME: 101>
This is the amount of time it takes to create a unit

### TOTAL_MISSILES        = <ObjectAttribute.TOTAL_MISSILES: 102>
This is the number of projectiles a unit fires. The Chu Ko Nu fires 3 and the Elite Chu Ko Nu fires 5

### FOOD_COSTS        = <ObjectAttribute.FOOD_COSTS: 103>
The food cost of a unit

### WOOD_COSTS        = <ObjectAttribute.WOOD_COSTS: 104>
The wood cost of a unit

### GOLD_COSTS        = <ObjectAttribute.GOLD_COSTS: 105>
The gold cost of a unit

### STONE_COSTS        = <ObjectAttribute.STONE_COSTS: 106>
The stone cost of a unit

### MAXIMUM_TOTAL_MISSILES        = <ObjectAttribute.MAXIMUM_TOTAL_MISSILES: 107>
The maximum number of projectiles a unit can fire when other units are garrisoned inside of it. A castle fires 5 projectiles by default but can fire more if units are garrisoned inside it. This attribute controls the maximum number of those

### GARRISON_HEAL_RATE        = <ObjectAttribute.GARRISON_HEAL_RATE: 108>
The rate measured in HP/s at which garissoned units are healed inside a given building

### REGENERATION_RATE        = <ObjectAttribute.REGENERATION_RATE: 109>
The rate measured in HP/minute at which units heal themselves. This value is overridden to 30 HP/minute if the flag for Self Regeneration is set in the Hero Status of a unit

### POPULATION        = <ObjectAttribute.POPULATION: 110>
Modifies the population headroom storage of a unit. Negative values = require population (units), positive values = give population (houses). This is not a real attribute that exists in A.G.E., just seems like a way to edit the population heardroom provided by a unit

### MINIMUM_CONVERSION_TIME_MODIFIER        = <ObjectAttribute.MINIMUM_CONVERSION_TIME_MODIFIER: 111>
Adds to the minimum time required to convert the unit

- Notes:

By default, units have a 4 monk second minimum conversion time
The overall minimum conversion time for all units is also affected by Convert Resist Min Adjustment

### MAXIMUM_CONVERSION_TIME_MODIFIER        = <ObjectAttribute.MAXIMUM_CONVERSION_TIME_MODIFIER: 112>
Adds to the maximum time after which a unit conversion is forced

- Notes:

By default, units have a 10 monk second maximum conversion time
The overall maximum conversion time for all units is also affected by Convert Resist Max Adjustment

### CONVERSION_CHANCE_MODIFIER        = <ObjectAttribute.CONVERSION_CHANCE_MODIFIER: 113>
The probability of conversion every monk second is divided by this value for the unit

- Notes:

The overall conversion probability for all units is also affected by Conversion Resistance

### FORMATION_CATEGORY        = <ObjectAttribute.FORMATION_CATEGORY: 114>
Control where the units in formation

- Flags:

- 0: Not using formation

- 1: Mobile

- 2: Body

- 3: Ranged

- 4: Long Ranged

- 5: Protected

### AREA_DAMAGE        = <ObjectAttribute.AREA_DAMAGE: 115>
Blast damage multiplier to non directly targeted units. Blast damage to non directly targeted units is a fixed value if this is negative

### DAMAGE_REFLECTION        = <ObjectAttribute.DAMAGE_REFLECTION: 118>
Damage percentage of the received damage to be reflected on the attacker (only for melee damage)

### FRIENDLY_FIRE_DAMAGE        = <ObjectAttribute.FRIENDLY_FIRE_DAMAGE: 119>
Blast damage multiplier to non directly targeted units. Blast damage to non directly targeted units is a fixed value if this is negative

### REGENERATION_HP_PERCENT        = <ObjectAttribute.REGENERATION_HP_PERCENT: 120>
Percentage of the unit’s max HP that is regenerated over a minute

### ABILITY_BUTTON_ICON_ID        = <ObjectAttribute.ABILITY_BUTTON_ICON_ID: 121>
Override for Transform/Active Ability Icon. Uses ID from Materials.json

### ABILITY_SHORT_TOOLTIP_ID        = <ObjectAttribute.ABILITY_SHORT_TOOLTIP_ID: 122>
Override for Transform/Active Ability Short Tooltip

### ABILITY_EXTENDED_TOOLTIP_ID        = <ObjectAttribute.ABILITY_EXTENDED_TOOLTIP_ID: 123>
Override for Transform/Active Ability Long Tooltip

### ABILITY_HOTKEY_ACTION        = <ObjectAttribute.ABILITY_HOTKEY_ACTION: 124>
button_action_list when pressing button/hotkey for the ability or transformation

### CHARGE_PROJECTILE_UNIT        = <ObjectAttribute.CHARGE_PROJECTILE_UNIT: 125>
Blast damage multiplier to non directly targeted units. Blast damage to non directly targeted units is a fixed value if this is negative

### AVAILABLE_UNIT_FLAG        = <ObjectAttribute.AVAILABLE_UNIT_FLAG: 126>
When Disabled flag 2 or 4 is set, sets value for number of trainable unit. Will use units paired in LinkedUnits.json to count them together

### DISABLED_UNIT_FLAG        = <ObjectAttribute.DISABLED_UNIT_FLAG: 127>
Enable/Disable a unit

- Flags:

- 1: Disabled

- 2: Limited training. Cannot be retrained after death

- 4: Limited training. Can be retrained after death

### ATTACK_PRIORITY        = <ObjectAttribute.ATTACK_PRIORITY: 128>
Defines what type of target the unit will prioritize

- Flags:

- 1: Units > Buildings

- 2: Buildings > Units

- 3: Buildings only

### INVULNERABILITY_LEVEL        = <ObjectAttribute.INVULNERABILITY_LEVEL: 129>
Sets an HP threshold after which a unit no longer receives damage when attacked

- Flags:

- > 0: Multiplier of Base HP

- < 0: Fixed value of HP

### GARRISON_FIREPOWER        = <ObjectAttribute.GARRISON_FIREPOWER: 130>
Adds to the damage of the unit to calculate the number of garrison arrows to fire

- Flags:

- > 0: Acts as multiplier

- < 0: Flat dps value added to the unit’s dps

### ATTACK_GRAPHIC_2        = <ObjectAttribute.ATTACK_GRAPHIC_2: 131>
Second attack graphic of the unit; alternates with the first attack graphic when assigned

### COMMAND_SOUND        = <ObjectAttribute.COMMAND_SOUND: 132>
TODO

### COMMAND_SOUND_EVENT        = <ObjectAttribute.COMMAND_SOUND_EVENT: 133>
TODO

### MOVE_SOUND        = <ObjectAttribute.MOVE_SOUND: 134>
TODO

### MOVE_SOUND_EVENT        = <ObjectAttribute.MOVE_SOUND_EVENT: 135>
TODO

### CONSTRUCTION_SOUND        = <ObjectAttribute.CONSTRUCTION_SOUND: 136>
TODO

### CONSTRUCTION_SOUND_EVENT        = <ObjectAttribute.CONSTRUCTION_SOUND_EVENT: 137>
TODO

### TRANSFORM_SOUND        = <ObjectAttribute.TRANSFORM_SOUND: 138>
TODO

### TRANSFORM_SOUND_EVENT        = <ObjectAttribute.TRANSFORM_SOUND_EVENT: 139>
TODO

### RUN_PATTERN        = <ObjectAttribute.RUN_PATTERN: 140>
Double-click selection will select all units which have the same value for this

- Flags:

- 255: Special value that defaults double-click selection to select by unit ID.

### INTERFACE_KIND        = <ObjectAttribute.INTERFACE_KIND: 141>
TODO

### COMBAT_LEVEL        = <ObjectAttribute.COMBAT_LEVEL: 142>
TODO

### INTERACTION_MODE        = <ObjectAttribute.INTERACTION_MODE: 143>
TODO

### MINIMAP_MODE        = <ObjectAttribute.MINIMAP_MODE: 144>
TODO

### TRAILING_UNIT        = <ObjectAttribute.TRAILING_UNIT: 145>
TODO

### TRAIL_MODE        = <ObjectAttribute.TRAIL_MODE: 146>
TODO

### TRAIL_DENSITY        = <ObjectAttribute.TRAIL_DENSITY: 147>
TODO

### PROJECTILE_GRAPHIC_DISPLACEMENT_X        = <ObjectAttribute.PROJECTILE_GRAPHIC_DISPLACEMENT_X: 148>
TODO

### PROJECTILE_GRAPHIC_DISPLACEMENT_Y        = <ObjectAttribute.PROJECTILE_GRAPHIC_DISPLACEMENT_Y: 149>
TODO

### PROJECTILE_GRAPHIC_DISPLACEMENT_Z        = <ObjectAttribute.PROJECTILE_GRAPHIC_DISPLACEMENT_Z: 150>
TODO

### PROJECTILE_SPAWNING_AREA_WIDTH        = <ObjectAttribute.PROJECTILE_SPAWNING_AREA_WIDTH: 151>
TODO

### PROJECTILE_SPAWNING_AREA_LENGTH        = <ObjectAttribute.PROJECTILE_SPAWNING_AREA_LENGTH: 152>
TODO

### PROJECTILE_SPAWNING_AREA_RANDOMNESS        = <ObjectAttribute.PROJECTILE_SPAWNING_AREA_RANDOMNESS: 153>
TODO

### DAMAGE_GRAPHICS_ENTRY_MOD        = <ObjectAttribute.DAMAGE_GRAPHICS_ENTRY_MOD: 154>
Determines the index at which damage graphic/damage graphic percent/damage graphic apply mode values are changed via effects in XS.

- Notes:

- Multiply by N to insert a new entry at index N, and then set entry mod to N

- Multiply by -(N+1) to delete index N, and then set entry mod to N

- Multiply with 255 (32767 also works) to append an entry at the end, and set the entry mod to the last index

- Multiply with -255 (-32768 also works) to delete the index at the end, and set entry mod to the new last index

- Note that inserting a new entry copies the existing last entry in the list as the default

### DAMAGE_GRAPHICS_TOTAL_NUM        = <ObjectAttribute.DAMAGE_GRAPHICS_TOTAL_NUM: 155>
The length of the damage sprites list. Can be set to shrink/extend the list (duplicates the last entry when extending).

### DAMAGE_GRAPHIC_PERCENT        = <ObjectAttribute.DAMAGE_GRAPHIC_PERCENT: 156>
The damage percent at which this sprite starts to be applied. This sprite remains active until the damage percent of the next damage sprite entry

### DAMAGE_GRAPHIC_APPLY_MODE        = <ObjectAttribute.DAMAGE_GRAPHIC_APPLY_MODE: 157>
The apply mode for this damage sprite.

- Notes:

- 0: Overlay flames on building

- 1: Overlay randomly

- 2: Replace (walls)

### TRAIN_LOCATIONS_ENTRY_MOD        = <ObjectAttribute.TRAIN_LOCATIONS_ENTRY_MOD: 158>
Determines the index at which train location/train button/train time/hotkey values are modified via effects in XS.

- Notes:

- Multiply by N to insert a new entry at index N, and then set entry mod to N

- Multiply by -(N+1) to delete index N, and then set entry mod to N

- Multiply with 32767 to append an entry at the end, and set the entry mod to the last index

- Multiply with -32768 to delete the index at the end, and set entry mod to the new last index

- Note that inserting a new entry copies the existing last entry in the list as the default

### TRAIN_LOCATIONS_TOTAL_NUM        = <ObjectAttribute.TRAIN_LOCATIONS_TOTAL_NUM: 159>
The length of the train locations list. Can be set to shrink/extend the list (duplicates the last entry when extending).

### ADD_ARMOR_TYPE        = <ObjectAttribute.ADD_ARMOR_TYPE: 160>
Setting this creates a new armor class in the targeted object/unit

- Notes:

Note: You still need to set the value of the class using the regular damage class modification effect.

### ADD_ATTACK_TYPE        = <ObjectAttribute.ADD_ATTACK_TYPE: 161>
Setting this creates a new attack class in the targeted object/unit

- Notes:

Note: You still need to set the value of the class using the regular damage class modification effect.

### CHARGE_TARGET        = <ObjectAttribute.CHARGE_TARGET: 162>
TODO

### SIZE_CLASS        = <ObjectAttribute.SIZE_CLASS: 163>
Controls garrison type properties

- Notes:

- 0: Legacy object_group dependent behaviour

- 1: Civilian

- 2: Infantry

- 3: Cavalry

- 4: Religious

- 5: Livestock

- 6: Siege

- 7: Ships

- 8: Unused

### REMOVE_ARMOR_TYPE        = <ObjectAttribute.REMOVE_ARMOR_TYPE: 164>
Setting this removes an existing armor class in the targeted object/unit

### REMOVE_ATTACK_TYPE        = <ObjectAttribute.REMOVE_ATTACK_TYPE: 165>
Setting this removes an existing attack class in the targeted object/unit

### UNDEAD_FLAG        = <ObjectAttribute.UNDEAD_FLAG: 166>
Changes behaviour related to death of an object

- Flags:

- 0: Default

- 1: Show Undead Graphic

- 2: Ignore In Kill Stats

- 4: Garrison Invincibility

### BUILD_AND_GO_AWAY        = <ObjectAttribute.BUILD_AND_GO_AWAY: 167>
When set, removes this building after it is built

### TYPE_FIRST_STORAGE        = <ObjectAttribute.TYPE_FIRST_STORAGE: 168>
The resource ID of the first attribute storage

### TYPE_SECOND_STORAGE        = <ObjectAttribute.TYPE_SECOND_STORAGE: 169>
The resource ID of the second attribute storage

### TYPE_THIRD_STORAGE        = <ObjectAttribute.TYPE_THIRD_STORAGE: 170>
The resource ID of the third attribute storage

### STORE_FLAG_FIRST_STORAGE        = <ObjectAttribute.STORE_FLAG_FIRST_STORAGE: 171>
The store flag of the first attribute storage

### STORE_FLAG_SECOND_STORAGE        = <ObjectAttribute.STORE_FLAG_SECOND_STORAGE: 172>
The store flag of the second attribute storage

### STORE_FLAG_THIRD_STORAGE        = <ObjectAttribute.STORE_FLAG_THIRD_STORAGE: 173>
The store flag of the third attribute storage

### AMOUNT_FIRST_COST        = <ObjectAttribute.AMOUNT_FIRST_COST: 174>
The amount for the first cost

### AMOUNT_SECOND_COST        = <ObjectAttribute.AMOUNT_SECOND_COST: 175>
The amount for the second cost

### AMOUNT_THIRD_COST        = <ObjectAttribute.AMOUNT_THIRD_COST: 176>
The amount for the third cost

### TYPE_FIRST_COST        = <ObjectAttribute.TYPE_FIRST_COST: 177>
The type of first cost

### TYPE_SECOND_COST        = <ObjectAttribute.TYPE_SECOND_COST: 178>
The type of second cost

### TYPE_THIRD_COST        = <ObjectAttribute.TYPE_THIRD_COST: 179>
The type of third cost

### DEDUCT_FLAG_FIRST_COST        = <ObjectAttribute.DEDUCT_FLAG_FIRST_COST: 180>
The deduct flag for the first cost

### DEDUCT_FLAG_SECOND_COST        = <ObjectAttribute.DEDUCT_FLAG_SECOND_COST: 181>
The deduct flag for the second cost

### DEDUCT_FLAG_THIRD_COST        = <ObjectAttribute.DEDUCT_FLAG_THIRD_COST: 182>
The deduct flag for the third cost

### SPAWNING_GRAPHIC        = <ObjectAttribute.SPAWNING_GRAPHIC: 183>
The graphic shown when a unit spawns

### UPGRADE_GRAPHIC        = <ObjectAttribute.UPGRADE_GRAPHIC: 184>
The graphic shown when a unit upgrades

### FLY_MODE        = <ObjectAttribute.FLY_MODE: 185>
Unknown

- Flags:

- 0: All units

- 1: All projectiles

### CAN_BE_GATHERED        = <ObjectAttribute.CAN_BE_GATHERED: 186>
For tracking gatherable resources. Unknown

- Flags:

- 0: All units

- 1: Resources like gold/stone etc.

### HILL_MODE        = <ObjectAttribute.HILL_MODE: 187>
Building placement restrictions around hills

- Flags:

- 0: No Restriction (Farms)

- 1: No Corners of Hills (Unused)

- 2: Flat Only (TCs)

- 3: Allows One Elevation Difference (Most Buildings)

### DOPPELGANGER        = <ObjectAttribute.DOPPELGANGER: 188>
Unknown

### GATHER_GROUP        = <ObjectAttribute.GATHER_GROUP: 189>
Unknown

### TASK_SWAP_GROUP        = <ObjectAttribute.TASK_SWAP_GROUP: 190>
Controls which units can swap with each other when attempting to find a valid task from all their task lists

- Flags:

- 0: None

- 1: Male Villagers

- 2: Female Villagers

- 3: Fishing Ships

### PLACEMENT_TERRAIN1        = <ObjectAttribute.PLACEMENT_TERRAIN1: 191>
Restricts placement on one of these two terrains

### PLACEMENT_TERRAIN2        = <ObjectAttribute.PLACEMENT_TERRAIN2: 192>
Restricts placement on one of these two terrains

### PLACEMENT_CENTER_TERRAIN_1        = <ObjectAttribute.PLACEMENT_CENTER_TERRAIN_1: 193>
Restricts placement such that the anchor tile of the unit must be on one of these two terrains

### PLACEMENT_CENTER_TERRAIN_2        = <ObjectAttribute.PLACEMENT_CENTER_TERRAIN_2: 194>
Restricts placement such that the anchor tile of the unit must be on one of these two terrains

### INITIATED_TECH_ID        = <ObjectAttribute.INITIATED_TECH_ID: 195>
Initiates this technology on being built

### MIN_SIZE_MULTIPLIER        = <ObjectAttribute.MIN_SIZE_MULTIPLIER: 196>
Unknown

### SELECTION_OUTLINE_SIZE_X        = <ObjectAttribute.SELECTION_OUTLINE_SIZE_X: 197>
The size of the selection outline along X

### SELECTION_OUTLINE_SIZE_Y        = <ObjectAttribute.SELECTION_OUTLINE_SIZE_Y: 198>
The size of the selection outline along Y

### SELECTION_OUTLINE_SIZE_Z        = <ObjectAttribute.SELECTION_OUTLINE_SIZE_Z: 199>
The size of the selection outline along Z.

### CLEARANCE_SIZE_X        = <ObjectAttribute.CLEARANCE_SIZE_X: 200>
Unknown

### CLEARANCE_SIZE_Y        = <ObjectAttribute.CLEARANCE_SIZE_Y: 201>
Unknown

### STACK_UNIT        = <ObjectAttribute.STACK_UNIT: 202>
Additional unit placed directly on top of this unit

### HEAD_UNIT        = <ObjectAttribute.HEAD_UNIT: 203>
The unit that annexes get attached to

### TRANSFORM_UNIT        = <ObjectAttribute.TRANSFORM_UNIT: 204>
Unpacks into this unit

### PILE_UNIT        = <ObjectAttribute.PILE_UNIT: 205>
Additional blood unit that only appears when a building is destroyed but not when deleted

### ANNEX_UNIT_1        = <ObjectAttribute.ANNEX_UNIT_1: 206>
First annex unit

### ANNEX_UNIT_2        = <ObjectAttribute.ANNEX_UNIT_2: 207>
Second annex unit

### ANNEX_UNIT_3        = <ObjectAttribute.ANNEX_UNIT_3: 208>
Third annex unit

### ANNEX_UNIT_4        = <ObjectAttribute.ANNEX_UNIT_4: 209>
Fourth annex unit

### ANNEX_UNIT_1_OFFSET_X        = <ObjectAttribute.ANNEX_UNIT_1_OFFSET_X: 210>
Offset for the first annex unit from the main unit along the X direction

### ANNEX_UNIT_1_OFFSET_Y        = <ObjectAttribute.ANNEX_UNIT_1_OFFSET_Y: 211>
Offset for the first annex unit from the main unit along the Y direction

### ANNEX_UNIT_2_OFFSET_X        = <ObjectAttribute.ANNEX_UNIT_2_OFFSET_X: 212>
Offset for the second annex unit from the main unit along the X direction

### ANNEX_UNIT_2_OFFSET_Y        = <ObjectAttribute.ANNEX_UNIT_2_OFFSET_Y: 213>
Offset for the second annex unit from the main unit along the Y direction

### ANNEX_UNIT_3_OFFSET_X        = <ObjectAttribute.ANNEX_UNIT_3_OFFSET_X: 214>
Offset for the third annex unit from the main unit along the X direction

### ANNEX_UNIT_3_OFFSET_Y        = <ObjectAttribute.ANNEX_UNIT_3_OFFSET_Y: 215>
Offset for the third annex unit from the main unit along the Y direction

### ANNEX_UNIT_4_OFFSET_X        = <ObjectAttribute.ANNEX_UNIT_4_OFFSET_X: 216>
Offset for the fourth annex unit from the main unit along the X direction

### ANNEX_UNIT_4_OFFSET_Y        = <ObjectAttribute.ANNEX_UNIT_4_OFFSET_Y: 217>
Offset for the fourth annex unit from the main unit along the Y direction

### MOVE_ALGORITHM        = <ObjectAttribute.MOVE_ALGORITHM: 218>
Unknown

### SPACING_MODIFIER        = <ObjectAttribute.SPACING_MODIFIER: 219>
Unknown

### CAN_BURN        = <ObjectAttribute.CAN_BURN: 220>
Gives flames to buildings when set to 1 when damaged. Unknown

### GATHER_FLAG        = <ObjectAttribute.GATHER_FLAG: 221>
For resources, similar to Can Be Gathered. Unknown


### class     ObjectClass(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the object class in the game. Used in a lot of effects
and conditions, like 'Kill Object', 'Objects in Area' under the name 'Object Group'.

Examples

### ARCHER        = <ObjectClass.ARCHER: 0>

### ARTIFACT        = <ObjectClass.ARTIFACT: 1>

### TRADE_BOAT        = <ObjectClass.TRADE_BOAT: 2>

### BUILDING        = <ObjectClass.BUILDING: 3>

### CIVILIAN        = <ObjectClass.CIVILIAN: 4>

### OCEAN_FISH        = <ObjectClass.OCEAN_FISH: 5>

### INFANTRY        = <ObjectClass.INFANTRY: 6>

### BERRY_BUSH        = <ObjectClass.BERRY_BUSH: 7>

### STONE_MINE        = <ObjectClass.STONE_MINE: 8>

### PREY_ANIMAL        = <ObjectClass.PREY_ANIMAL: 9>

### PREDATOR_ANIMAL        = <ObjectClass.PREDATOR_ANIMAL: 10>

### MISCELLANEOUS        = <ObjectClass.MISCELLANEOUS: 11>

### CAVALRY        = <ObjectClass.CAVALRY: 12>

### SIEGE_WEAPON        = <ObjectClass.SIEGE_WEAPON: 13>

### TERRAIN        = <ObjectClass.TERRAIN: 14>

### TREE        = <ObjectClass.TREE: 15>

### TREE_STUMP        = <ObjectClass.TREE_STUMP: 16>

### HEALER        = <ObjectClass.HEALER: 17>

### MONK        = <ObjectClass.MONK: 18>

### TRADE_CART        = <ObjectClass.TRADE_CART: 19>

### TRANSPORT_BOAT        = <ObjectClass.TRANSPORT_BOAT: 20>

### FISHING_BOAT        = <ObjectClass.FISHING_BOAT: 21>

### WARSHIP        = <ObjectClass.WARSHIP: 22>

### CONQUISTADOR        = <ObjectClass.CONQUISTADOR: 23>

### WAR_ELEPHANT        = <ObjectClass.WAR_ELEPHANT: 24>

### HERO        = <ObjectClass.HERO: 25>

### ELEPHANT_ARCHER        = <ObjectClass.ELEPHANT_ARCHER: 26>

### WALL        = <ObjectClass.WALL: 27>

### PHALANX        = <ObjectClass.PHALANX: 28>

### DOMESTIC_ANIMAL        = <ObjectClass.DOMESTIC_ANIMAL: 29>

### FLAG        = <ObjectClass.FLAG: 30>

### DEEP_SEA_FISH        = <ObjectClass.DEEP_SEA_FISH: 31>

### GOLD_MINE        = <ObjectClass.GOLD_MINE: 32>

### SHORE_FISH        = <ObjectClass.SHORE_FISH: 33>

### CLIFF        = <ObjectClass.CLIFF: 34>

### PETARD        = <ObjectClass.PETARD: 35>

### CAVALRY_ARCHER        = <ObjectClass.CAVALRY_ARCHER: 36>

### DOPPELGANGER        = <ObjectClass.DOPPELGANGER: 37>

### BIRD        = <ObjectClass.BIRD: 38>

### GATE        = <ObjectClass.GATE: 39>

### SALVAGE_PILE        = <ObjectClass.SALVAGE_PILE: 40>

### RESOURCE_PILE        = <ObjectClass.RESOURCE_PILE: 41>

### RELIC        = <ObjectClass.RELIC: 42>

### MONKWITH_RELIC        = <ObjectClass.MONKWITH_RELIC: 43>

### HAND_CANNONEER        = <ObjectClass.HAND_CANNONEER: 44>

### TWO_HANDED_SWORDSMAN        = <ObjectClass.TWO_HANDED_SWORDSMAN: 45>

### PIKEMAN        = <ObjectClass.PIKEMAN: 46>

### SCOUT        = <ObjectClass.SCOUT: 47>

### ORE_MINE        = <ObjectClass.ORE_MINE: 48>

### FARM        = <ObjectClass.FARM: 49>

### SPEARMAN        = <ObjectClass.SPEARMAN: 50>

### PACKED_UNIT        = <ObjectClass.PACKED_UNIT: 51>

### TOWER        = <ObjectClass.TOWER: 52>

### BOARDING_BOAT        = <ObjectClass.BOARDING_BOAT: 53>

### UNPACKED_SIEGE_UNIT        = <ObjectClass.UNPACKED_SIEGE_UNIT: 54>

### BALLISTA        = <ObjectClass.BALLISTA: 55>

### RAIDER        = <ObjectClass.RAIDER: 56>

### CAVALRY_RAIDER        = <ObjectClass.CAVALRY_RAIDER: 57>

### LIVESTOCK        = <ObjectClass.LIVESTOCK: 58>

### KING        = <ObjectClass.KING: 59>

### MISC_BUILDING        = <ObjectClass.MISC_BUILDING: 60>

### CONTROLLED_ANIMAL        = <ObjectClass.CONTROLLED_ANIMAL: 61>

### OYSTERS        = <ObjectClass.OYSTERS: 63>

### EXPLOSION        = <ObjectClass.EXPLOSION: 64>


### class     ObjectModifyAttributeState(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the modification state of a unit used in the
modify object attribute effect.

Examples

### ALL        = <ObjectModifyAttributeState.ALL: 0>

### MODIFIED        = <ObjectModifyAttributeState.MODIFIED: 1>

### NOT_MODIFIED        = <ObjectModifyAttributeState.NOT_MODIFIED: 2>


### class     ObjectState(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the object state values used in the game. Used in the
'Object in Area' condition, 'Remove Object' effect, and unit creation.

Examples

### FOUNDATION        = <ObjectState.FOUNDATION: 0>

### ALMOST_ALIVE        = <ObjectState.ALMOST_ALIVE: 1>

### ALIVE        = <ObjectState.ALIVE: 2>

### DEAD        = <ObjectState.DEAD: 3>

### ALMOST_DEAD        = <ObjectState.ALMOST_DEAD: 4>

### REALLY_DEAD        = <ObjectState.REALLY_DEAD: 5>

### UNDEAD        = <ObjectState.UNDEAD: 6>

### REMOVE        = <ObjectState.REMOVE: 7>

### GOING        = <ObjectState.GOING: 8>


### class     ObjectType(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the object types in the game. Used in a lot of effects
and conditions, like 'Kill Object', 'Objects in Area'.

Examples

### OTHER        = <ObjectType.OTHER: 1>

### BUILDING        = <ObjectType.BUILDING: 2>

### CIVILIAN        = <ObjectType.CIVILIAN: 3>

### MILITARY        = <ObjectType.MILITARY: 4>


### class     ObstructionType(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values for the different obstruction types that can be used in the 'Modify
Attribute' effect with the 'ObstructionType' attribute.

Examples:

### SQUARE_OUTLINE_PASSABLE        = <ObstructionType.SQUARE_OUTLINE_PASSABLE: 0>
Square outline and passable

### SOLID_SQUARE_OUTLINE_COLLISION        = <ObstructionType.SOLID_SQUARE_OUTLINE_COLLISION: 2>
Solid square outline, and has collision box

### SQUARE_OUTLINE_COLLISION        = <ObstructionType.SQUARE_OUTLINE_COLLISION: 3>
Square outline, and has collision box

### NO_OUTLINE_PASSABLE        = <ObstructionType.NO_OUTLINE_PASSABLE: 4>
No outline, and passable

### ROUND_OUTLINE_COLLISION        = <ObstructionType.ROUND_OUTLINE_COLLISION: 5>
Round outline, and has collision box

### SOLID_SQUARE_OUTLINE_COLLISION_MOUNTAINS        = <ObstructionType.SOLID_SQUARE_OUTLINE_COLLISION_MOUNTAINS: 10>
Same as <ObstructionType.SOLID_SQUARE_OUTLINE_COLLISION: 2> but designed for mountains


### class     OcclusionMode(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntFlags):
This enum class provides the integer values for the different occlusion mode flags that can be used in the 'Modify
Attribute' effect with the 'OcclusionMode' attribute. This is a combinable bit field.

Examples

### NO_OCCLUSION        = <OcclusionMode.NO_OCCLUSION: 0>
No outline

### DISPLAY_OUTLINE        = <OcclusionMode.DISPLAY_OUTLINE: 1>
Display outline when behind other units that have flag 2

### OCCLUDES_OTHERS        = <OcclusionMode.OCCLUDES_OTHERS: 2>
Other units' outlines are rendered when they are behind this unit

### DISPLAY_OUTLINE_FOR_FOUNDATION        = <OcclusionMode.DISPLAY_OUTLINE_FOR_FOUNDATION: 4>
Display outline on this unit's foundation when behind other units that have flag


### class     Operation(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the operations in the game. Used in a lot of effects
like 'Modify Attribute' to control whether an attribute is set, added to, multiplied or divided by a value.

Examples

### SET        = <Operation.SET: 1>

### ADD        = <Operation.ADD: 2>

### SUBTRACT        = <Operation.SUBTRACT: 3>

### MULTIPLY        = <Operation.MULTIPLY: 4>

### DIVIDE        = <Operation.DIVIDE: 5>


### class     PanelLocation(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the panel positons in the game. Used in the 'Display
Information' effect.

Examples

### TOP        = <PanelLocation.TOP: 0>
Panel at the top of the screen. ~13% from the top

### MIDDLE        = <PanelLocation.MIDDLE: 1>
Panel between the top and the center of the screen. ~33% from the top

### BOTTOM        = <PanelLocation.BOTTOM: 2>
Panel close to the center of the screen. ~45% from the top


### class     ProjectileHitMode(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to references the different projectile hit mode settings that can
be used in the 'Modify Attribute' effect with the 'Projectile Hit Mode' attribute.

Examples

### TARGET_ONLY        = <ProjectileHitMode.TARGET_ONLY: 0>
Collide only with the targeted unit"

### ANY_PLAYER_UNIT        = <ProjectileHitMode.ANY_PLAYER_UNIT: 1>
Collide with any damage-able units in the path to the targeted unit"

### ANY_OBSTACLE        = <ProjectileHitMode.ANY_OBSTACLE: 2>
Collide with any unit in the path to the targeted unit


### class     ProjectileSmartMode(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntFlags):
This enum class provides the integer values used to reference the smart projectile flag values used in the game.
Used in the 'Modify Attribute' effect with the 'Projectile Smart Mode' attribute. This is a combainable bit field

Examples

### TARGET_CURRENT_LOCATION        = <ProjectileSmartMode.TARGET_CURRENT_LOCATION: 0>

### TARGET_FUTURE_LOCATION        = <ProjectileSmartMode.TARGET_FUTURE_LOCATION: 1>

### FULL_DAMAGE_ON_MISSED_HIT        = <ProjectileSmartMode.FULL_DAMAGE_ON_MISSED_HIT: 2>


### class     ProjectileVanishMode(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to references the different projectile vanish mode settings that
can be used in the 'Modify Attribute' effect with the 'Projectile Vanish Mode' attribute.

Examples

### DISAPPEAR_ON_IMPACT        = <ProjectileVanishMode.DISAPPEAR_ON_IMPACT: 0>

### PASS_THROUGH        = <ProjectileVanishMode.PASS_THROUGH: 1>

### ALWAYS_SPAWN_DEAD_UNIT        = <ProjectileVanishMode.ALWAYS_SPAWN_DEAD_UNIT: 2>


### class     SecondaryGameMode(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntFlags):
This enum class provides the integer values for the different secondary game modes.

Examples

### @staticmethod
This method combines the given hero status flags into an integer value

Args:
    empire_wars: If empire wars should be enabled
    sudden_death: If sudden death should be enabled
    regicide: If regicide should be enabled
    king_of_the_hill: If king of the hill should be enabled

Returns:
    An integer combining all the different hero status flags into one value

### NONE        = <SecondaryGameMode.NONE: 0>

### EMPIRE_WARS        = <SecondaryGameMode.EMPIRE_WARS: 1>

### SUDDEN_DEATH        = <SecondaryGameMode.SUDDEN_DEATH: 2>

### REGICIDE        = <SecondaryGameMode.REGICIDE: 4>

### KING_OF_THE_HILL        = <SecondaryGameMode.KING_OF_THE_HILL: 8>


### class     SelectionEffect(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values for the different selection effects that can be used in the 'Modify
Attribute' effect with the 'SelectionEffect' attribute.

Examples:

### HP_BAR        = <SelectionEffect.HP_BAR: 0>
Has hit point bar

### HP_BAR_OUTLINE        = <SelectionEffect.HP_BAR_OUTLINE: 1>
Has hit point bar, and outline

### NONE        = <SelectionEffect.NONE: 2>
No hit point bar, or outline

### OUTLINE        = <SelectionEffect.OUTLINE: 3>
No hit point bar, but has outline


### class     TechnologyState(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference technology state of a technology in the game. Used in
the 'Technology State' condition.

Examples

### DISABLED        = <TechnologyState.DISABLED: -1>

### NOT_READY        = <TechnologyState.NOT_READY: 0>
A tech that is not available to be researched (Bombard Tower is not ready before chemistry is researched)

### READY        = <TechnologyState.READY: 1>
A tech that is available to be researched (Bombard Tower is ready after chemistry is researched)

### RESEARCHING        = <TechnologyState.RESEARCHING: 2>
A tech that is currently being researched

### DONE        = <TechnologyState.DONE: 3>
A Tech that has already been researched

### QUEUED        = <TechnologyState.QUEUED: 4>
A tech that is waiting in queue to be researched


### class     TerrainRestrictions(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the terrain restriction IDs in the game. Used in the
'Modify Attribute' effects

Examples

### ALL        = <TerrainRestrictions.ALL: 0>
Used by terrain eyecandy and sundries

### LAND_AND_SHALLOWS        = <TerrainRestrictions.LAND_AND_SHALLOWS: 1>
Used by part of animals

### BEACH        = <TerrainRestrictions.BEACH: 2>

### WATER_SMALL_TRAIL        = <TerrainRestrictions.WATER_SMALL_TRAIL: 3>
Used by most ships and sea gate

### LAND        = <TerrainRestrictions.LAND: 4>
Used by most land buildings

### NOTHING        = <TerrainRestrictions.NOTHING: 5>

### WATER_NO_TRAIL        = <TerrainRestrictions.WATER_NO_TRAIL: 6>
Used by docks

### ALL_EXCEPT_WATER        = <TerrainRestrictions.ALL_EXCEPT_WATER: 7>
Used by land troops

### LAND_EXCEPT_FARM        = <TerrainRestrictions.LAND_EXCEPT_FARM: 8>
Used by land resources

### NOTHING_2        = <TerrainRestrictions.NOTHING_2: 9>

### LAND_AND_BEACH        = <TerrainRestrictions.LAND_AND_BEACH: 10>
Used by land walls and gates

### LAND_EXCEPT_FARM_2        = <TerrainRestrictions.LAND_EXCEPT_FARM_2: 11>
Used by trees and mountains

### ALL_EXCEPT_WATER_BRIDGE_CANNON        = <TerrainRestrictions.ALL_EXCEPT_WATER_BRIDGE_CANNON: 12>

### WATER_MEDIUM_TRAIL        = <TerrainRestrictions.WATER_MEDIUM_TRAIL: 13>
Used by big fish and fishing ship

### ALL_EXCEPT_WATER_BRIDGE_ARROW        = <TerrainRestrictions.ALL_EXCEPT_WATER_BRIDGE_ARROW: 14>

### WATER_LARGE_TRAIL        = <TerrainRestrictions.WATER_LARGE_TRAIL: 15>
Only used by transport ship

### GRASS_AND_BEACH        = <TerrainRestrictions.GRASS_AND_BEACH: 16>

### WATER_AND_BRIDGE_EXCEPT_BEACH        = <TerrainRestrictions.WATER_AND_BRIDGE_EXCEPT_BEACH: 17>

### ALL_EXCEPT_WATER_BRIDGE_SPEAR        = <TerrainRestrictions.ALL_EXCEPT_WATER_BRIDGE_SPEAR: 18>

### ONLY_WATER_AND_ICE        = <TerrainRestrictions.ONLY_WATER_AND_ICE: 19>
Used by fish

### ALL_EXCEPT_WATER_WHEEL        = <TerrainRestrictions.ALL_EXCEPT_WATER_WHEEL: 20>
Used by units with wheels, such as Rams and Scorpions

### SHALLOW_WATER        = <TerrainRestrictions.SHALLOW_WATER: 21>

### ALL_DART        = <TerrainRestrictions.ALL_DART: 22>

### ALL_ARROW_FIRE        = <TerrainRestrictions.ALL_ARROW_FIRE: 23>
Only used by Arrows with fire (After chemistry)

### ALL_CANNON_FIRE        = <TerrainRestrictions.ALL_CANNON_FIRE: 24>
Only used by Cannon balls (After chemistry)

### ALL_SPEAR_FIRE        = <TerrainRestrictions.ALL_SPEAR_FIRE: 25>
Only used by Spears with fire (After chemistry)

### ALL_DART_FIRE        = <TerrainRestrictions.ALL_DART_FIRE: 26>
Only used by Darts with fire (After chemistry)

### ALL_LASER        = <TerrainRestrictions.ALL_LASER: 27>
Only used by Projectile Laser with id 1595

### ALL_EXCEPT_WATER_CAVALRY        = <TerrainRestrictions.ALL_EXCEPT_WATER_CAVALRY: 28>
Such as Cavalry Archer, Cavalry, Conquistador, Missionary and Flaming Camel

### ALL_EXCEPT_WATER_PACKET_TREBUCHET        = <TerrainRestrictions.ALL_EXCEPT_WATER_PACKET_TREBUCHET: 29>
All types of Trebuchet(Packed)

### WATER_SMALLEST_TRAIL        = <TerrainRestrictions.WATER_SMALLEST_TRAIL: 30>
Used by medium ships, such as Trade Cog, Fire Galley and Longboat


### class     TimeUnit(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the unit of time used in an effect. Used in the
'Display Timer' effect.

Examples

### YEARS        = <TimeUnit.YEARS: 0>
In-Game years. A year is 5 seconds in-game time.

### MINUTES        = <TimeUnit.MINUTES: 1>
In-Game minutes.

### SECONDS        = <TimeUnit.SECONDS: 2>
In-Game seconds.

### MINUTES_AND_SECONDS        = <TimeUnit.MINUTES_AND_SECONDS: 3>
In-Game Minutes abd seconds.


### class     UnitAIAction(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the unit AI actions in the game. Used in the 'Object
Has Action' condition.

Examples

### ANY        = <UnitAIAction.ANY: 0>
Fires if the unit has any action

### ATTACK        = <UnitAIAction.ATTACK: 1>
Fires when the unit is attacking any unit

### BUILD        = <UnitAIAction.BUILD: 3>
Unknown

### CONVERT        = <UnitAIAction.CONVERT: 5>
Fires when a monk or missionary is converting any unit

### DEFEND        = <UnitAIAction.DEFEND: 2>
Unknown

### ENTER        = <UnitAIAction.ENTER: 18>
Unknown

### EVADE        = <UnitAIAction.EVADE: 17>
Unknown

### EXPLORE        = <UnitAIAction.EXPLORE: 6>
Unknown

### FOLLOW        = <UnitAIAction.FOLLOW: 13>
Fires when a unit is following any unit

### GATHER        = <UnitAIAction.GATHER: 10>
Fires when a villager or fishing ship is gathering resources

### HEAL        = <UnitAIAction.HEAL: 4>
Fires when a monk or missionary is healing another unit

### HUNT        = <UnitAIAction.HUNT: 14>
Fires when a hunter is gathering from a corpse of a hunted animal. Does NOT fire when the hunter is chasing the
animal

### IDLE        = <UnitAIAction.IDLE: 24>
Fires when a unit is standing still

### MOVE        = <UnitAIAction.MOVE: 11>
Fires when a unit is moving

### PATROL        = <UnitAIAction.PATROL: 12>
Fires when a unit is patrolling

### RELIC        = <UnitAIAction.RELIC: 23>
Unknown

### REPAIR        = <UnitAIAction.REPAIR: 19>
Fires when a villager is repairing any other unit

### RESEARCH        = <UnitAIAction.RESEARCH: 21>
Unknown

### RETREAT        = <UnitAIAction.RETREAT: 9>
Unknown

### RUNAWAY        = <UnitAIAction.RUNAWAY: 8>
Unknown

### STOP        = <UnitAIAction.STOP: 7>
Unknown

### TRADE        = <UnitAIAction.TRADE: 16>
Fires when a trade cart is returning to any of its own player's markets

### TRAIN        = <UnitAIAction.TRAIN: 20>
Unknown

### TRANSPORT        = <UnitAIAction.TRANSPORT: 15>
Unknown

### UNLOAD        = <UnitAIAction.UNLOAD: 22>
Fires when a transport ship is tasked to unload objects. Note that the transport gets stuck in this state!


### class     UnitTrait(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntFlags):
This enum class provides the integer values used to references the different unit trait flags that can be used in
the 'Modify Attribute' effect with the 'Unit Trait' attribute.

Examples

### GARRISONABLE        = <UnitTrait.GARRISONABLE: 1>

### SHIP        = <UnitTrait.SHIP: 2>

### BUILD_BUILDING        = <UnitTrait.BUILD_BUILDING: 4>

### TRANSFORMABLE        = <UnitTrait.TRANSFORMABLE: 8>

### AUTO_SCOUT        = <UnitTrait.AUTO_SCOUT: 16>


### class     VictoryCondition(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to references the different victory conditions that can be set
using the Global Victory tab in the in-game editor.

Examples

### STANDARD        = <VictoryCondition.STANDARD: 0>

### CONQUEST        = <VictoryCondition.CONQUEST: 1>

### SCORE        = <VictoryCondition.SCORE: 2>

### TIME_LIMIT        = <VictoryCondition.TIME_LIMIT: 3>

### CUSTOM        = <VictoryCondition.CUSTOM: 4>

### SECONDARY_GAME_MODE        = <VictoryCondition.SECONDARY_GAME_MODE: 6>


### class     VictoryTimerType(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the different types of victory timer types.

Examples

### WONDER_TIMER        = <VictoryTimerType.WONDER_TIMER: 0>

### RELIC_TIMER        = <VictoryTimerType.RELIC_TIMER: 1>

### KING_OF_THE_HILL_TIMER        = <VictoryTimerType.KING_OF_THE_HILL_TIMER: 2>


### class     VisibilityState(AoE2ScenarioParser.datasets.dataset_enum._DataSetIntEnums):
This enum class provides the integer values used to reference the visibility state of a player for another player
in the game. Used in the 'Set Visibility State' and 'Change Object Visibility' effects.

Examples

### VISIBLE        = <VisibilityState.VISIBLE: 0>

### EXPLORED        = <VisibilityState.EXPLORED: 1>

### INVISIBLE        = <VisibilityState.INVISIBLE: 2>


### datasets/


### class     UnitInfo(AoE2ScenarioParser.datasets.support.info_dataset_base.InfoDatasetBase):
This class provides information about most of the units in the game. Information about the following properties of
a unit is found in this class:

- Unit ID

- Icon ID

- Dead Unit ID

- HotKey ID

- If the unit is a gaia only unit (e.g. deer, boar, etc.)

Methods

Inherited Methods from class InfoDatasetBase

Examples

### @staticmethod
Args:
    exclude_female: if set to true, exclude the female villagers
    exclude_male: if set to true, exclude the male villagers

Returns:
    A list of villager UnitInfo objects

### @staticmethod
Args:
    exclude_elite_units: if set to False, exclude the elite unique units
    exclude_non_elite_units: if set to False, exclude the non elite unique units
    exclude_castle_units: if set to False, exclude the castle unique units
    exclude_non_castle_units: if set to False, excludes the unique units not trained at the castle
    include_chronicles: if set to True, will include all unique units added in the chronicles dlc

Returns:
    A list of unique unit UniInfo objects

### @staticmethod
Args:
    exclude_scouts: if set to False, exclude the scout regional units
    exclude_elite_units: if set to False, exclude the elite regional units
    exclude_non_elite_units: if set to False, exclude the non elite regional units
    include_chronicles: if set to True, will include all regional units added in the chronicles dlc
Returns:
    A list of regional unit UniInfo objects

### BROWN_BEAR        = <UnitInfo.BROWN_BEAR: (486, 151, 489, 16712, True)>

### BUTTERFLY1        = <UnitInfo.BUTTERFLY1: (1608, -1, -1, 16716, True)>

### BUTTERFLY2        = <UnitInfo.BUTTERFLY2: (1609, -1, -1, 16716, True)>

### BUTTERFLY3        = <UnitInfo.BUTTERFLY3: (1610, -1, -1, 16716, True)>

### CROCODILE        = <UnitInfo.CROCODILE: (1031, 193, 1032, 16060, True)>

### DEER        = <UnitInfo.DEER: (65, 3, 43, 16071, True)>

### DIRE_WOLF        = <UnitInfo.DIRE_WOLF: (89, 7, 237, 16075, True)>

### ELEPHANT        = <UnitInfo.ELEPHANT: (1301, 179, 1332, 16722, True)>

### FALCON        = <UnitInfo.FALCON: (1056, 5, -1, 16058, True)>

### HAWK        = <UnitInfo.HAWK: (96, 283, -1, 16073, True)>

### IBEX        = <UnitInfo.IBEX: (1239, 267, 1240, 16071, True)>

### IRON_BOAR        = <UnitInfo.IRON_BOAR: (810, 98, 356, 16710, True)>

### JAGUAR        = <UnitInfo.JAGUAR: (812, 111, 813, 16712, True)>

### JAVELINA        = <UnitInfo.JAVELINA: (822, 588, 356, 16722, True)>

### KOMODO_DRAGON        = <UnitInfo.KOMODO_DRAGON: (1135, 226, 1136, 16163, True)>

### LION        = <UnitInfo.LION: (1029, 194, 1030, 16059, True)>

### MACAW        = <UnitInfo.MACAW: (816, 284, -1, 16716, True)>

### OSTRICH        = <UnitInfo.OSTRICH: (1026, 196, 1027, 16071, True)>

### RABID_WOLF        = <UnitInfo.RABID_WOLF: (202, 7, 237, 16652, True)>

### RHINOCEROS        = <UnitInfo.RHINOCEROS: (1139, 225, 1140, 16172, True)>

### SEAGULLS        = <UnitInfo.SEAGULLS: (303, -1, -1, 16716, True)>

### SNOW_LEOPARD        = <UnitInfo.SNOW_LEOPARD: (1241, 268, 1242, 16060, True)>

### STORK        = <UnitInfo.STORK: (1028, 285, -1, 16058, True)>

### STORMY_DOG        = <UnitInfo.STORMY_DOG: (862, 159, -1, 16764, True)>

### TIGER        = <UnitInfo.TIGER: (1137, 227, 1138, 16170, True)>

### VULTURE        = <UnitInfo.VULTURE: (1305, 286, -1, 16716, True)>

### WILD_BACTRIAN_CAMEL        = <UnitInfo.WILD_BACTRIAN_CAMEL: (1247, 266, 1238, 16735, True)>

### WILD_BOAR        = <UnitInfo.WILD_BOAR: (48, 98, 356, 16406, True)>

### WILD_CAMEL        = <UnitInfo.WILD_CAMEL: (884, 135, 898, 16735, True)>

### WILD_HORSE_A        = <UnitInfo.WILD_HORSE_A: (835, 112, 815, 16735, True)>

### GREY_WOLF        = <UnitInfo.GREY_WOLF: (126, 7, 237, 16075, True)>

### ZEBRA        = <UnitInfo.ZEBRA: (1019, 192, 1020, 16071, True)>

### MOVEABLE_MAP_REVEALER_A        = <UnitInfo.MOVEABLE_MAP_REVEALER_A: (0, -1, -1, 16000, False)>

### ALFRED_THE_ALPACA        = <UnitInfo.ALFRED_THE_ALPACA: (1300, 177, 1331, 16469, False)>

### AMAZON_ARCHER        = <UnitInfo.AMAZON_ARCHER: (850, 165, 1325, 16683, False)>

### AMAZON_WARRIOR        = <UnitInfo.AMAZON_WARRIOR: (825, 166, 1324, 16667, False)>

### ARAMBAI        = <UnitInfo.ARAMBAI: (1126, 230, 1127, 16101, False)>

### ARBALESTER        = <UnitInfo.ARBALESTER: (492, 90, 496, 16418, False)>

### ARCHER        = <UnitInfo.ARCHER: (4, 17, 3, 16083, False)>

### BACTRIAN_CAMEL        = <UnitInfo.BACTRIAN_CAMEL: (1237, 266, 1238, 16714, False)>

### BALLISTA_ELEPHANT        = <UnitInfo.BALLISTA_ELEPHANT: (1120, 231, 1121, 16101, False)>

### BANDIT        = <UnitInfo.BANDIT: (299, 8, 2, 16098, False)>

### BATTERING_RAM        = <UnitInfo.BATTERING_RAM: (1258, 74, 23, 16094, False)>

### BATTLE_ELEPHANT        = <UnitInfo.BATTLE_ELEPHANT: (1132, 228, 1133, 16733, False)>

### BERSERK        = <UnitInfo.BERSERK: (692, 38, 693, 16574, False)>

### BOMBARD_CANNON        = <UnitInfo.BOMBARD_CANNON: (36, 30, 16, 16093, False)>

### BOYAR        = <UnitInfo.BOYAR: (876, 114, 877, 16101, False)>

### CAMEL        = <UnitInfo.CAMEL: (897, 135, 898, 16714, False)>

### CAMEL_ARCHER        = <UnitInfo.CAMEL_ARCHER: (1007, 191, 1008, 16101, False)>

### CAMEL_RIDER        = <UnitInfo.CAMEL_RIDER: (329, 78, 113, 16416, False)>

### CANNON_GALLEON        = <UnitInfo.CANNON_GALLEON: (420, 55, -1, 16287, False)>

### CANOE        = <UnitInfo.CANOE: (778, 164, -1, 16106, False)>

### CAPPED_RAM        = <UnitInfo.CAPPED_RAM: (422, 63, 423, 16289, False)>

### CARAVEL        = <UnitInfo.CARAVEL: (1004, 198, -1, 16106, False)>

### CART        = <UnitInfo.CART: (1338, 34, 205, 16100, False)>

### CATAPHRACT        = <UnitInfo.CATAPHRACT: (40, 35, 27, 16101, False)>

### CAVALIER        = <UnitInfo.CAVALIER: (283, 49, 139, 16070, False)>

### CAVALRY_ARCHER        = <UnitInfo.CAVALRY_ARCHER: (39, 19, 34, 16085, False)>

### IMPERIAL_CENTURION        = <UnitInfo.IMPERIAL_CENTURION: (275, 138, 277, 16451, False)>

### CHAMPION        = <UnitInfo.CHAMPION: (567, 72, 568, 16469, False)>

### CHU_KO_NU        = <UnitInfo.CHU_KO_NU: (73, 36, 28, 16102, False)>

### COBRA_CAR        = <UnitInfo.COBRA_CAR: (748, 142, -1, 16658, False)>

### CONDOTTIERO        = <UnitInfo.CONDOTTIERO: (882, 134, 883, 16679, False)>

### CONQUISTADOR        = <UnitInfo.CONQUISTADOR: (771, 106, 772, 16687, False)>

### COW_A        = <UnitInfo.COW_A: (705, 150, 843, 16498, False)>

### COW_B        = <UnitInfo.COW_B: (1596, 150, 1597, 16498, False)>

### COW_C        = <UnitInfo.COW_C: (1598, 150, 1599, 16498, False)>

### COW_D        = <UnitInfo.COW_D: (1600, 150, 1601, 16498, False)>

### CROSSBOWMAN        = <UnitInfo.CROSSBOWMAN: (24, 18, 26, 16084, False)>

### DEMOLITION_RAFT        = <UnitInfo.DEMOLITION_RAFT: (1104, 202, -1, 16424, False)>

### DEMOLITION_SHIP        = <UnitInfo.DEMOLITION_SHIP: (527, 84, -1, 16424, False)>

### DONKEY        = <UnitInfo.DONKEY: (846, 158, 848, 16100, False)>

### DRAGON_SHIP        = <UnitInfo.DRAGON_SHIP: (1302, 178, -1, 16426, False)>

### EAGLE_SCOUT        = <UnitInfo.EAGLE_SCOUT: (751, 109, 754, 16671, False)>

### EAGLE_WARRIOR        = <UnitInfo.EAGLE_WARRIOR: (753, 148, 1116, 16671, False)>

### EASTERN_SWORDSMAN        = <UnitInfo.EASTERN_SWORDSMAN: (894, 186, 895, 16081, False)>

### ELEPHANT_ARCHER        = <UnitInfo.ELEPHANT_ARCHER: (873, 393, 874, 16744, False)>

### ELITE_ARAMBAI        = <UnitInfo.ELITE_ARAMBAI: (1128, 504, 1127, 16101, False)>

### ELITE_BALLISTA_ELEPHANT        = <UnitInfo.ELITE_BALLISTA_ELEPHANT: (1122, 502, 1121, 16101, False)>

### ELITE_BATTLE_ELEPHANT        = <UnitInfo.ELITE_BATTLE_ELEPHANT: (1134, 246, 1154, 16733, False)>

### ELITE_BERSERK        = <UnitInfo.ELITE_BERSERK: (694, 485, 695, 16101, False)>

### ELITE_BOYAR        = <UnitInfo.ELITE_BOYAR: (878, 494, 877, 16101, False)>

### ELITE_CAMEL_ARCHER        = <UnitInfo.ELITE_CAMEL_ARCHER: (1009, 498, 1008, 16101, False)>

### ELITE_CANNON_GALLEON        = <UnitInfo.ELITE_CANNON_GALLEON: (691, 298, -1, 16287, False)>

### ELITE_CARAVEL        = <UnitInfo.ELITE_CARAVEL: (1006, 497, -1, 16106, False)>

### ELITE_CATAPHRACT        = <UnitInfo.ELITE_CATAPHRACT: (553, 476, 27, 16101, False)>

### ELITE_CHU_KO_NU        = <UnitInfo.ELITE_CHU_KO_NU: (559, 482, 28, 16101, False)>

### ELITE_CONQUISTADOR        = <UnitInfo.ELITE_CONQUISTADOR: (773, 489, 772, 16101, False)>

### ELITE_EAGLE_WARRIOR        = <UnitInfo.ELITE_EAGLE_WARRIOR: (752, 149, 1117, 16673, False)>

### ELITE_ELEPHANT_ARCHER        = <UnitInfo.ELITE_ELEPHANT_ARCHER: (875, 93, 1667, 16744, False)>

### ELITE_GBETO        = <UnitInfo.ELITE_GBETO: (1015, 500, 1014, 16101, False)>

### ELITE_GENITOUR        = <UnitInfo.ELITE_GENITOUR: (1012, 499, 1011, 16417, False)>

### ELITE_GENOESE_CROSSBOWMAN        = <UnitInfo.ELITE_GENOESE_CROSSBOWMAN: (868, 492, 867, 16101, False)>

### ELITE_HUSKARL        = <UnitInfo.ELITE_HUSKARL: (555, 478, 62, 16104, False)>

### ELITE_JAGUAR_WARRIOR        = <UnitInfo.ELITE_JAGUAR_WARRIOR: (726, 486, 750, 16101, False)>

### ELITE_JANISSARY        = <UnitInfo.ELITE_JANISSARY: (557, 480, 107, 16101, False)>

### ELITE_KAMAYUK        = <UnitInfo.ELITE_KAMAYUK: (881, 495, 880, 16101, False)>

### ELITE_KARAMBIT_WARRIOR        = <UnitInfo.ELITE_KARAMBIT_WARRIOR: (1125, 503, 1124, 16101, False)>

### ELITE_KESHIK        = <UnitInfo.ELITE_KESHIK: (1230, 507, 1229, 16101, False)>

### ELITE_KIPCHAK        = <UnitInfo.ELITE_KIPCHAK: (1233, 508, 1232, 16101, False)>

### ELITE_KONNIK        = <UnitInfo.ELITE_KONNIK: (1227, 506, 1226, 16101, False)>

### ELITE_KONNIK_DISMOUNTED        = <UnitInfo.ELITE_KONNIK_DISMOUNTED: (1253, 510, 1257, 16411, False)>

### ELITE_LEITIS        = <UnitInfo.ELITE_LEITIS: (1236, 509, 1235, 16101, False)>

### ELITE_LONGSHIP        = <UnitInfo.ELITE_LONGSHIP: (533, 474, -1, 16106, False)>

### ELITE_LONGBOWMAN        = <UnitInfo.ELITE_LONGBOWMAN: (530, 472, 115, 16101, False)>

### ELITE_MAGYAR_HUSZAR        = <UnitInfo.ELITE_MAGYAR_HUSZAR: (871, 493, 870, 16101, False)>

### ELITE_MAMELUKE        = <UnitInfo.ELITE_MAMELUKE: (556, 479, 44, 16101, False)>

### ELITE_MANGUDAI        = <UnitInfo.ELITE_MANGUDAI: (561, 484, 135, 16101, False)>

### ELITE_ORGAN_GUN        = <UnitInfo.ELITE_ORGAN_GUN: (1003, 496, 1002, 16101, False)>

### ELITE_PLUMED_ARCHER        = <UnitInfo.ELITE_PLUMED_ARCHER: (765, 488, 764, 16101, False)>

### ELITE_RATTAN_ARCHER        = <UnitInfo.ELITE_RATTAN_ARCHER: (1131, 505, 1130, 16101, False)>

### ELITE_SAMURAI        = <UnitInfo.ELITE_SAMURAI: (560, 483, 151, 16101, False)>

### ELITE_SHOTEL_WARRIOR        = <UnitInfo.ELITE_SHOTEL_WARRIOR: (1018, 501, 1017, 16101, False)>

### ELITE_SKIRMISHER        = <UnitInfo.ELITE_SKIRMISHER: (6, 21, 100, 16087, False)>

### ELITE_STEPPE_LANCER        = <UnitInfo.ELITE_STEPPE_LANCER: (1372, 274, 1373, 16746, False)>

### ELITE_TARKAN        = <UnitInfo.ELITE_TARKAN: (757, 487, 756, 16675, False)>

### ELITE_TEUTONIC_KNIGHT        = <UnitInfo.ELITE_TEUTONIC_KNIGHT: (554, 477, 181, 16101, False)>

### ELITE_THROWING_AXEMAN        = <UnitInfo.ELITE_THROWING_AXEMAN: (531, 473, 157, 16101, False)>

### ELITE_TURTLE_SHIP        = <UnitInfo.ELITE_TURTLE_SHIP: (832, 491, -1, 16106, False)>

### ELITE_WAR_ELEPHANT        = <UnitInfo.ELITE_WAR_ELEPHANT: (558, 481, 136, 16101, False)>

### ELITE_WAR_WAGON        = <UnitInfo.ELITE_WAR_WAGON: (829, 490, 828, 16101, False)>

### ELITE_WOAD_RAIDER        = <UnitInfo.ELITE_WOAD_RAIDER: (534, 475, 233, 16101, False)>

### FAST_FIRE_SHIP        = <UnitInfo.FAST_FIRE_SHIP: (532, 85, -1, 16429, False)>

### FIRE_GALLEY        = <UnitInfo.FIRE_GALLEY: (1103, 203, -1, 16426, False)>

### FIRE_SHIP        = <UnitInfo.FIRE_SHIP: (529, 86, -1, 16426, False)>

### FISHING_SHIP        = <UnitInfo.FISHING_SHIP: (13, 24, -1, 16090, False)>

### FLAMETHROWER        = <UnitInfo.FLAMETHROWER: (188, 144, 189, 16109, False)>

### FLAMING_CAMEL        = <UnitInfo.FLAMING_CAMEL: (1263, 270, -1, 16734, False)>

### FURIOUS_THE_MONKEY_BOY        = <UnitInfo.FURIOUS_THE_MONKEY_BOY: (860, 132, 861, 16763, False)>

### GALLEON        = <UnitInfo.GALLEON: (442, 60, -1, 16309, False)>

### GALLEY        = <UnitInfo.GALLEY: (539, 87, -1, 16436, False)>

### GBETO        = <UnitInfo.GBETO: (1013, 197, 1014, 16101, False)>

### GENITOUR        = <UnitInfo.GENITOUR: (1010, 201, 1011, 16417, False)>

### GENOESE_CROSSBOWMAN        = <UnitInfo.GENOESE_CROSSBOWMAN: (866, 133, 867, 16101, False)>

### GOAT        = <UnitInfo.GOAT: (1060, 200, 1061, 16061, False)>

### GOOSE        = <UnitInfo.GOOSE: (1243, 265, 1244, 16061, False)>

### HALBERDIER        = <UnitInfo.HALBERDIER: (359, 104, 502, 16078, False)>

### HAND_CANNONEER        = <UnitInfo.HAND_CANNONEER: (5, 22, 98, 16086, False)>

### HEAVY_CAMEL_RIDER        = <UnitInfo.HEAVY_CAMEL_RIDER: (330, 79, 495, 16416, False)>

### HEAVY_CAVALRY_ARCHER        = <UnitInfo.HEAVY_CAVALRY_ARCHER: (474, 71, 631, 16412, False)>

### HEAVY_CROSSBOWMAN        = <UnitInfo.HEAVY_CROSSBOWMAN: (493, 133, 867, 16101, False)>

### HEAVY_DEMOLITION_SHIP        = <UnitInfo.HEAVY_DEMOLITION_SHIP: (528, 83, -1, 16425, False)>

### HEAVY_PIKEMAN        = <UnitInfo.HEAVY_PIKEMAN: (892, 136, 893, 16410, False)>

### HEAVY_SCORPION        = <UnitInfo.HEAVY_SCORPION: (542, 89, 543, 16439, False)>

### HEAVY_SWORDSMAN        = <UnitInfo.HEAVY_SWORDSMAN: (76, 184, 99, 16077, False)>

### HORSE_A        = <UnitInfo.HORSE_A: (814, 112, 815, 16714, False)>

### HORSE_B        = <UnitInfo.HORSE_B: (1356, 112, 1357, 16714, False)>

### HORSE_C        = <UnitInfo.HORSE_C: (1602, 112, 1603, 16714, False)>

### HORSE_D        = <UnitInfo.HORSE_D: (1604, 112, 1605, 16714, False)>

### HORSE_E        = <UnitInfo.HORSE_E: (1606, 112, 1607, 16714, False)>

### HUSKARL        = <UnitInfo.HUSKARL: (41, 50, 62, 16104, False)>

### HUSSAR        = <UnitInfo.HUSSAR: (441, 103, 480, 16661, False)>

### IMPERIAL_CAMEL_RIDER        = <UnitInfo.IMPERIAL_CAMEL_RIDER: (207, 185, 300, 16416, False)>

### IMPERIAL_SKIRMISHER        = <UnitInfo.IMPERIAL_SKIRMISHER: (1155, 229, 1156, 16087, False)>

### INVISIBLE_OBJECT_A        = <UnitInfo.INVISIBLE_OBJECT_A: (1291, -1, -1, 16000, False)>

### IROQUOIS_WARRIOR        = <UnitInfo.IROQUOIS_WARRIOR: (1374, 297, 1375, 16113, False)>

### JAGUAR_WARRIOR        = <UnitInfo.JAGUAR_WARRIOR: (725, 110, 750, 16667, False)>

### JANISSARY        = <UnitInfo.JANISSARY: (46, 39, 107, 16105, False)>

### JUNK        = <UnitInfo.JUNK: (15, 211, -1, 16092, False)>

### KAMAYUK        = <UnitInfo.KAMAYUK: (879, 97, 880, 16110, False)>

### KARAMBIT_WARRIOR        = <UnitInfo.KARAMBIT_WARRIOR: (1123, 233, 1124, 16101, False)>

### KESHIK        = <UnitInfo.KESHIK: (1228, 251, 1229, 16101, False)>

### KHAN        = <UnitInfo.KHAN: (1275, 258, 1277, 16458, False)>

### KING        = <UnitInfo.KING: (434, 48, 435, 16301, False)>

### KIPCHAK        = <UnitInfo.KIPCHAK: (1231, 252, 1232, 16108, False)>

### KNIGHT        = <UnitInfo.KNIGHT: (38, 1, 111, 16068, False)>

### KONNIK        = <UnitInfo.KONNIK: (1225, 249, 1226, 16101, False)>

### KONNIK_DISMOUNTED        = <UnitInfo.KONNIK_DISMOUNTED: (1252, 250, 1257, 16411, False)>

### IMPERIAL_LEGIONARY        = <UnitInfo.IMPERIAL_LEGIONARY: (1, 139, 2, 16669, False)>

### LEITIS        = <UnitInfo.LEITIS: (1234, 253, 1235, 16101, False)>

### LIGHT_CAVALRY        = <UnitInfo.LIGHT_CAVALRY: (546, 91, 547, 16444, False)>

### LLAMA_A        = <UnitInfo.LLAMA_A: (305, 156, 780, 16498, False)>

### LONG_SWORDSMAN        = <UnitInfo.LONG_SWORDSMAN: (77, 13, 180, 16081, False)>

### LONGSHIP        = <UnitInfo.LONGSHIP: (250, 40, -1, 16106, False)>

### LONGBOWMAN        = <UnitInfo.LONGBOWMAN: (8, 41, 115, 16107, False)>

### MAGYAR_HUSZAR        = <UnitInfo.MAGYAR_HUSZAR: (869, 99, 870, 16101, False)>

### MAMELUKE        = <UnitInfo.MAMELUKE: (282, 37, 44, 16103, False)>

### MAN_AT_ARMS        = <UnitInfo.MAN_AT_ARMS: (75, 10, 154, 16080, False)>

### MANGONEL        = <UnitInfo.MANGONEL: (280, 27, 121, 16095, False)>

### MANGUDAI        = <UnitInfo.MANGUDAI: (11, 42, 135, 16108, False)>

### MERCHANT        = <UnitInfo.MERCHANT: (1572, 346, 1573, 16301, False)>

### MILITIA        = <UnitInfo.MILITIA: (74, 8, 152, 16079, False)>

### MISSIONARY        = <UnitInfo.MISSIONARY: (775, 107, 776, 16691, False)>

### MONK        = <UnitInfo.MONK: (125, 33, 134, 16099, False)>

### MONK_WITH_RELIC        = <UnitInfo.MONK_WITH_RELIC: (286, 33, 134, 16380, False)>

### NINJA        = <UnitInfo.NINJA: (1145, 299, 1147, 16110, False)>

### NORSE_WARRIOR        = <UnitInfo.NORSE_WARRIOR: (361, 140, 362, 16081, False)>

### ONAGER        = <UnitInfo.ONAGER: (550, 101, 675, 16448, False)>

### ORGAN_GUN        = <UnitInfo.ORGAN_GUN: (1001, 190, 1002, 16101, False)>

### OX_CART        = <UnitInfo.OX_CART: (1271, 263, 1272, 16100, False)>

### OX_WAGON        = <UnitInfo.OX_WAGON: (1273, 264, 1274, 16100, False)>

### PALADIN        = <UnitInfo.PALADIN: (569, 2, 570, 16471, False)>

### WAR_PENGUIN        = <UnitInfo.WAR_PENGUIN: (639, 157, 641, 16469, False)>

### PETARD        = <UnitInfo.PETARD: (440, 113, -1, 16660, False)>

### PHOTONMAN        = <UnitInfo.PHOTONMAN: (1577, 300, 1578, 16043, False)>

### PIG        = <UnitInfo.PIG: (1245, 269, 1246, 16061, False)>

### PIKEMAN        = <UnitInfo.PIKEMAN: (358, 11, 501, 16078, False)>

### PLUMED_ARCHER        = <UnitInfo.PLUMED_ARCHER: (763, 108, 764, 16683, False)>

### PRIEST        = <UnitInfo.PRIEST: (1023, 294, 1024, 16099, False)>

### PRIEST_WITH_RELIC        = <UnitInfo.PRIEST_WITH_RELIC: (1400, 294, 1024, 16380, False)>

### QUEEN        = <UnitInfo.QUEEN: (1292, 168, 1328, 16302, False)>

### RATTAN_ARCHER        = <UnitInfo.RATTAN_ARCHER: (1129, 232, 1130, 16101, False)>

### RELIC_CART        = <UnitInfo.RELIC_CART: (1304, 295, 285, 16082, False)>

### ROYAL_JANISSARY        = <UnitInfo.ROYAL_JANISSARY: (52, 296, 1576, 16455, False)>

### SAMURAI        = <UnitInfo.SAMURAI: (291, 44, 151, 16110, False)>

### SCORPION        = <UnitInfo.SCORPION: (279, 80, 149, 16096, False)>

### SCOUT_CAVALRY        = <UnitInfo.SCOUT_CAVALRY: (448, 64, 449, 16326, False)>

### SHARKATZOR        = <UnitInfo.SHARKATZOR: (1222, 352, -1, 16458, False)>

### SHEEP        = <UnitInfo.SHEEP: (594, 96, 595, 16498, False)>

### SHOTEL_WARRIOR        = <UnitInfo.SHOTEL_WARRIOR: (1016, 195, 1017, 16101, False)>

### SIEGE_ONAGER        = <UnitInfo.SIEGE_ONAGER: (588, 102, 589, 16493, False)>

### SIEGE_RAM        = <UnitInfo.SIEGE_RAM: (548, 73, 549, 16446, False)>

### SIEGE_TOWER        = <UnitInfo.SIEGE_TOWER: (1105, 212, 1107, 16445, False)>

### SKIRMISHER        = <UnitInfo.SKIRMISHER: (7, 20, 238, 16088, False)>

### SLINGER        = <UnitInfo.SLINGER: (185, 143, 186, 16743, False)>

### SPEARMAN        = <UnitInfo.SPEARMAN: (93, 31, 140, 16078, False)>

### STEPPE_LANCER        = <UnitInfo.STEPPE_LANCER: (1370, 273, 1371, 16746, False)>

### TARKAN        = <UnitInfo.TARKAN: (755, 105, 756, 16675, False)>

### TEUTONIC_KNIGHT        = <UnitInfo.TEUTONIC_KNIGHT: (25, 45, 181, 16112, False)>

### THROWING_AXEMAN        = <UnitInfo.THROWING_AXEMAN: (281, 46, 157, 16111, False)>

### TORCH_A_CONVERTABLE        = <UnitInfo.TORCH_A_CONVERTABLE: (854, -1, -1, 16753, False)>

### TORCH_B_CONVERTABLE        = <UnitInfo.TORCH_B_CONVERTABLE: (1377, -1, -1, 16753, False)>

### TRADE_CART_EMPTY        = <UnitInfo.TRADE_CART_EMPTY: (128, 34, 178, 16100, False)>

### TRADE_CART_FULL        = <UnitInfo.TRADE_CART_FULL: (204, 34, 205, 16100, False)>

### TRADE_COG        = <UnitInfo.TRADE_COG: (17, 23, -1, 16089, False)>

### TRANSPORT_SHIP        = <UnitInfo.TRANSPORT_SHIP: (545, 95, -1, 16443, False)>

### TREBUCHET        = <UnitInfo.TREBUCHET: (42, 28, 194, 16097, False)>

### TREBUCHET_PACKED        = <UnitInfo.TREBUCHET_PACKED: (331, 29, 735, 16381, False)>

### TURKEY        = <UnitInfo.TURKEY: (833, 115, 834, 16733, False)>

### TURTLE_SHIP        = <UnitInfo.TURTLE_SHIP: (831, 116, -1, 16106, False)>

### TWO_HANDED_SWORDSMAN        = <UnitInfo.TWO_HANDED_SWORDSMAN: (473, 12, 500, 16411, False)>

### VILLAGER_MALE        = <UnitInfo.VILLAGER_MALE: (83, 15, 224, 16121, False)>

### VILLAGER_FEMALE        = <UnitInfo.VILLAGER_FEMALE: (293, 16, 211, 16121, False)>

### VILLAGER_MALE_BUILDER        = <UnitInfo.VILLAGER_MALE_BUILDER: (118, 330, 225, 16122, False)>

### VILLAGER_FEMALE_BUILDER        = <UnitInfo.VILLAGER_FEMALE_BUILDER: (212, 329, 213, 16122, False)>

### VILLAGER_MALE_FARMER        = <UnitInfo.VILLAGER_MALE_FARMER: (259, 332, 226, 16123, False)>

### VILLAGER_FEMALE_FARMER        = <UnitInfo.VILLAGER_FEMALE_FARMER: (214, 331, 215, 16123, False)>

### VILLAGER_MALE_FISHERMAN        = <UnitInfo.VILLAGER_MALE_FISHERMAN: (56, 332, 58, 16499, False)>

### VILLAGER_FEMALE_FISHERMAN        = <UnitInfo.VILLAGER_FEMALE_FISHERMAN: (57, 331, 60, 16499, False)>

### VILLAGER_MALE_FORAGER        = <UnitInfo.VILLAGER_MALE_FORAGER: (120, 332, 353, 16402, False)>

### VILLAGER_FEMALE_FORAGER        = <UnitInfo.VILLAGER_FEMALE_FORAGER: (354, 331, 355, 16402, False)>

### VILLAGER_MALE_GOLD_MINER        = <UnitInfo.VILLAGER_MALE_GOLD_MINER: (579, 334, 229, 16482, False)>

### VILLAGER_FEMALE_GOLD_MINER        = <UnitInfo.VILLAGER_FEMALE_GOLD_MINER: (581, 333, 221, 16482, False)>

### VILLAGER_MALE_HUNTER        = <UnitInfo.VILLAGER_MALE_HUNTER: (122, 332, 227, 16124, False)>

### VILLAGER_FEMALE_HUNTER        = <UnitInfo.VILLAGER_FEMALE_HUNTER: (216, 331, 217, 16124, False)>

### VILLAGER_MALE_LUMBERJACK        = <UnitInfo.VILLAGER_MALE_LUMBERJACK: (123, 339, 228, 16125, False)>

### VILLAGER_FEMALE_LUMBERJACK        = <UnitInfo.VILLAGER_FEMALE_LUMBERJACK: (218, 338, 219, 16125, False)>

### VILLAGER_MALE_REPAIRER        = <UnitInfo.VILLAGER_MALE_REPAIRER: (156, 330, 225, 16127, False)>

### VILLAGER_FEMALE_REPAIRER        = <UnitInfo.VILLAGER_FEMALE_REPAIRER: (222, 329, 213, 16127, False)>

### VILLAGER_MALE_SHEPHERD        = <UnitInfo.VILLAGER_MALE_SHEPHERD: (592, 332, 593, 16496, False)>

### VILLAGER_FEMALE_SHEPHERD        = <UnitInfo.VILLAGER_FEMALE_SHEPHERD: (590, 331, 591, 16496, False)>

### VILLAGER_MALE_STONE_MINER        = <UnitInfo.VILLAGER_MALE_STONE_MINER: (124, 336, 229, 16126, False)>

### VILLAGER_FEMALE_STONE_MINER        = <UnitInfo.VILLAGER_FEMALE_STONE_MINER: (220, 335, 221, 16126, False)>

### VILLAGER_MALE_OYSTER_GATHERER        = <UnitInfo.VILLAGER_MALE_OYSTER_GATHERER: (2333, 229, 334, 16482, False)>

### VILLAGER_FEMALE_OYSTER_GATHERER        = <UnitInfo.VILLAGER_FEMALE_OYSTER_GATHERER: (2334, 221, 333, 16482, False)>

### VILLAGER_MALE_HERDER        = <UnitInfo.VILLAGER_MALE_HERDER: (1892, 332, 226, 16123, False)>

### VILLAGER_FEMALE_HERDER        = <UnitInfo.VILLAGER_FEMALE_HERDER: (1891, 331, 215, 16123, False)>

### VMDL        = <UnitInfo.VMDL: (206, 337, -1, 16656, False)>

### WAR_ELEPHANT        = <UnitInfo.WAR_ELEPHANT: (239, 43, 136, 16109, False)>

### WAR_GALLEY        = <UnitInfo.WAR_GALLEY: (21, 25, -1, 16091, False)>

### WAR_WAGON        = <UnitInfo.WAR_WAGON: (827, 117, 828, 16727, False)>

### WATER_BUFFALO        = <UnitInfo.WATER_BUFFALO: (1142, 224, 1143, 16175, False)>

### WOAD_RAIDER        = <UnitInfo.WOAD_RAIDER: (232, 47, 233, 16113, False)>

### XOLOTL_WARRIOR        = <UnitInfo.XOLOTL_WARRIOR: (1570, 351, 1571, 16736, False)>

### BOARDER_GALLEY        = <UnitInfo.BOARDER_GALLEY: (536, 82, -1, 16703, False)>

### HUSKARL_BARRACKS        = <UnitInfo.HUSKARL_BARRACKS: (759, 50, 62, 16748, False)>

### ELITE_HUSKARL_BARRACKS        = <UnitInfo.ELITE_HUSKARL_BARRACKS: (761, 50, 62, 16748, False)>

### TARKAN_STABLE        = <UnitInfo.TARKAN_STABLE: (886, 105, 756, 16741, False)>

### ELITE_TARKAN_STABLE        = <UnitInfo.ELITE_TARKAN_STABLE: (887, 105, 756, 16741, False)>

### GENITOUR_ORIGINAL        = <UnitInfo.GENITOUR_ORIGINAL: (583, 19, 152, 16663, False)>

### ELITE_GENITOUR_ORIGINAL        = <UnitInfo.ELITE_GENITOUR_ORIGINAL: (596, 19, 152, 16665, False)>

### COUSTILLIER        = <UnitInfo.COUSTILLIER: (1655, 355, 1656, 16101, False)>

### ELITE_COUSTILLIER        = <UnitInfo.ELITE_COUSTILLIER: (1657, 511, 1656, 16101, False)>

### FLEMISH_MILITIA        = <UnitInfo.FLEMISH_MILITIA: (1699, 354, 1664, 16735, False)>

### FLEMISH_MILITIA_MALE        = <UnitInfo.FLEMISH_MILITIA_MALE: (1663, 354, 1664, 16469, False)>

### FLEMISH_MILITIA_FEMALE        = <UnitInfo.FLEMISH_MILITIA_FEMALE: (1697, 354, 1698, 16469, False)>

### SERJEANT        = <UnitInfo.SERJEANT: (1658, 356, 1662, 16104, False)>

### ELITE_SERJEANT        = <UnitInfo.ELITE_SERJEANT: (1659, 512, 1662, 16101, False)>

### SERJEANT_DONJON        = <UnitInfo.SERJEANT_DONJON: (1660, 356, 1662, 16101, False)>

### ELITE_SERJEANT_DONJON        = <UnitInfo.ELITE_SERJEANT_DONJON: (1661, 356, 1662, 16101, False)>

### CONDOTTIERO_PLACEHOLDER        = <UnitInfo.CONDOTTIERO_PLACEHOLDER: (184, 134, 883, 16679, False)>

### KONNIK_KREPOST        = <UnitInfo.KONNIK_KREPOST: (1254, 249, 1252, 16101, False)>

### ELITE_KONNIK_KREPOST        = <UnitInfo.ELITE_KONNIK_KREPOST: (1255, 249, 1253, 16101, False)>

### ELITE_KIPCHAK_CUMAN_MERCENARIES        = <UnitInfo.ELITE_KIPCHAK_CUMAN_MERCENARIES: (1260, 252, 1232, 16730, False)>

### FOOD_WOOD_GOLD_TRICKLE        = <UnitInfo.FOOD_WOOD_GOLD_TRICKLE: (1654, -1, -1, 16737, False)>

### CUMAN_DISABLED        = <UnitInfo.CUMAN_DISABLED: (1261, 114, 1232, 16108, False)>

### OUTLW        = <UnitInfo.OUTLW: (158, 17, 3, 16074, True)>

### RFARC        = <UnitInfo.RFARC: (571, 17, 572, 16474, False)>

### MONUMENT_RESOURCE_ENABLER        = <UnitInfo.MONUMENT_RESOURCE_ENABLER: (1639, 17, 572, 16464, False)>

### HUSSITE_WAGON        = <UnitInfo.HUSSITE_WAGON: (1704, 370, 1705, 16101, False)>

### ELITE_HUSSITE_WAGON        = <UnitInfo.ELITE_HUSSITE_WAGON: (1706, 514, 1705, 16101, False)>

### OBUCH        = <UnitInfo.OBUCH: (1701, 369, 1702, 16104, False)>

### ELITE_OBUCH        = <UnitInfo.ELITE_OBUCH: (1703, 513, 1702, 16101, False)>

### WINGED_HUSSAR        = <UnitInfo.WINGED_HUSSAR: (1707, 371, 1708, 16661, False)>

### HOUFNICE        = <UnitInfo.HOUFNICE: (1709, 372, 1710, 16093, False)>

### URUMI_SWORDSMAN        = <UnitInfo.URUMI_SWORDSMAN: (1735, 386, 1736, 16104, False)>

### MONK_WITH_TURKISH_RELIC        = <UnitInfo.MONK_WITH_TURKISH_RELIC: (309, 33, 134, 16361, False)>

### CRUSADER_KNIGHT        = <UnitInfo.CRUSADER_KNIGHT: (1723, 377, 1724, 16730, False)>

### ELITE_URUMI_SWORDSMAN        = <UnitInfo.ELITE_URUMI_SWORDSMAN: (1737, 515, 1736, 16101, False)>

### RATHA_MELEE        = <UnitInfo.RATHA_MELEE: (1738, 388, 1739, 16101, False)>

### ELITE_RATHA_MELEE        = <UnitInfo.ELITE_RATHA_MELEE: (1740, 516, 1739, 16101, False)>

### CHAKRAM_THROWER        = <UnitInfo.CHAKRAM_THROWER: (1741, 390, 1742, 16111, False)>

### ELITE_CHAKRAM_THROWER        = <UnitInfo.ELITE_CHAKRAM_THROWER: (1743, 517, 1742, 16101, False)>

### GHULAM        = <UnitInfo.GHULAM: (1747, 385, 1748, 16101, False)>

### ELITE_GHULAM        = <UnitInfo.ELITE_GHULAM: (1749, 518, 1748, 16101, False)>

### THIRISADAI        = <UnitInfo.THIRISADAI: (1750, 387, -1, 16457, False)>

### SHRIVAMSHA_RIDER        = <UnitInfo.SHRIVAMSHA_RIDER: (1751, 391, 1752, 16737, False)>

### ELITE_SHRIVAMSHA_RIDER        = <UnitInfo.ELITE_SHRIVAMSHA_RIDER: (1753, 519, 1752, 16737, False)>

### CAMEL_SCOUT        = <UnitInfo.CAMEL_SCOUT: (1755, 392, 1668, 16416, False)>

### RATHA_RANGED        = <UnitInfo.RATHA_RANGED: (1759, 389, 1760, 16727, False)>

### ELITE_RATHA_RANGED        = <UnitInfo.ELITE_RATHA_RANGED: (1761, 520, 1760, 16101, False)>

### ARMORED_ELEPHANT        = <UnitInfo.ARMORED_ELEPHANT: (1744, 394, 1745, 16494, False)>

### SIEGE_ELEPHANT        = <UnitInfo.SIEGE_ELEPHANT: (1746, 395, 1757, 16494, False)>

### SOGDIAN_CATAPHRACT        = <UnitInfo.SOGDIAN_CATAPHRACT: (1299, 181, 1401, 16451, False)>

### SPEARMAN_DONJON        = <UnitInfo.SPEARMAN_DONJON: (1786, 31, 140, 16078, False)>

### PIKEMAN_DONJON        = <UnitInfo.PIKEMAN_DONJON: (1787, 11, 501, 16408, False)>

### HALBERDIER_DONJON        = <UnitInfo.HALBERDIER_DONJON: (1788, 104, 502, 16409, False)>

### CENTURION        = <UnitInfo.CENTURION: (1790, 405, 1791, 16101, False)>

### ELITE_CENTURION        = <UnitInfo.ELITE_CENTURION: (1792, 521, 1791, 16101, False)>

### LEGIONARY        = <UnitInfo.LEGIONARY: (1793, 139, 1794, 16469, False)>

### DROMON        = <UnitInfo.DROMON: (1795, 406, -1, 16738, False)>

### GAZELLE        = <UnitInfo.GAZELLE: (1796, 404, 1797, 16071, True)>

### COMPOSITE_BOWMAN        = <UnitInfo.COMPOSITE_BOWMAN: (1800, 407, 1801, 16107, False)>

### ELITE_COMPOSITE_BOWMAN        = <UnitInfo.ELITE_COMPOSITE_BOWMAN: (1802, 522, 1801, 16101, False)>

### MONASPA        = <UnitInfo.MONASPA: (1803, 408, 1804, 16101, False)>

### ELITE_MONASPA        = <UnitInfo.ELITE_MONASPA: (1805, 523, 1804, 16101, False)>

### VILLAGER_MALE_MONASTERY        = <UnitInfo.VILLAGER_MALE_MONASTERY: (1810, 15, 224, 16691, False)>

### WARRIOR_PRIEST        = <UnitInfo.WARRIOR_PRIEST: (1811, 409, 1812, 16691, False)>

### WARRIOR_PRIEST_WITH_RELIC        = <UnitInfo.WARRIOR_PRIEST_WITH_RELIC: (1831, 409, 1812, 16380, False)>

### SAVAR        = <UnitInfo.SAVAR: (1813, 410, 1814, 16471, False)>

### QIZILBASH_WARRIOR        = <UnitInfo.QIZILBASH_WARRIOR: (1817, 412, 1818, 16101, False)>

### ELITE_QIZILBASH_WARRIOR        = <UnitInfo.ELITE_QIZILBASH_WARRIOR: (1829, 412, 1818, 16101, False)>

### IMMORTAL_MELEE        = <UnitInfo.IMMORTAL_MELEE: (2101, 621, 2103, 16104, False)>

### ELITE_IMMORTAL_MELEE        = <UnitInfo.ELITE_IMMORTAL_MELEE: (2102, 621, 2103, 16104, False)>

### STRATEGOS        = <UnitInfo.STRATEGOS: (2104, 624, 2106, 16104, False)>

### ELITE_STRATEGOS        = <UnitInfo.ELITE_STRATEGOS: (2105, 624, 2106, 16104, False)>

### STRATEGOS_WITH_TAXIARCHS        = <UnitInfo.STRATEGOS_WITH_TAXIARCHS: (2227, 624, 2106, 16104, False)>

### ELITE_STRATEGOS_WITH_TAXIARCHS        = <UnitInfo.ELITE_STRATEGOS_WITH_TAXIARCHS: (2228, 624, 2106, 16104, False)>

### HIPPEUS        = <UnitInfo.HIPPEUS: (2107, 623, 2109, 16104, False)>

### ELITE_HIPPEUS        = <UnitInfo.ELITE_HIPPEUS: (2108, 623, 2109, 16104, False)>

### HIPPEUS_WITH_AURA        = <UnitInfo.HIPPEUS_WITH_AURA: (2168, 623, 2109, -1, False)>

### ELITE_HIPPEUS_WITH_AURA        = <UnitInfo.ELITE_HIPPEUS_WITH_AURA: (2169, 623, 2109, -1, False)>

### HOPLITE        = <UnitInfo.HOPLITE: (2110, 625, 2112, 416013, False)>

### ELITE_HOPLITE        = <UnitInfo.ELITE_HOPLITE: (2111, 626, 2301, 416013, False)>

### HOPLITE_WITH_XYPHOS        = <UnitInfo.HOPLITE_WITH_XYPHOS: (2187, 625, 2112, 416013, False)>

### ELITE_HOPLITE_WITH_XYPHOS        = <UnitInfo.ELITE_HOPLITE_WITH_XYPHOS: (2188, 626, 2301, 416013, False)>

### LEMBOS        = <UnitInfo.LEMBOS: (2123, 656, -1, 416006, False)>

### WAR_LEMBOS        = <UnitInfo.WAR_LEMBOS: (2124, 657, -1, 416006, False)>

### HEAVY_LEMBOS        = <UnitInfo.HEAVY_LEMBOS: (2125, 658, -1, 416006, False)>

### ELITE_LEMBOS        = <UnitInfo.ELITE_LEMBOS: (2126, 659, -1, 416006, False)>

### MONOREME        = <UnitInfo.MONOREME: (2127, 661, -1, 416007, False)>

### BIREME        = <UnitInfo.BIREME: (2128, 662, -1, 416007, False)>

### TRIREME        = <UnitInfo.TRIREME: (2129, 663, -1, 416007, False)>

### GALLEY_ANTIQUITY        = <UnitInfo.GALLEY_ANTIQUITY: (2130, 664, -1, 416008, False)>

### WAR_GALLEY_ANTIQUITY        = <UnitInfo.WAR_GALLEY_ANTIQUITY: (2131, 666, -1, 416008, False)>

### ELITE_GALLEY        = <UnitInfo.ELITE_GALLEY: (2132, 665, -1, 416008, False)>

### INCENDIARY_RAFT        = <UnitInfo.INCENDIARY_RAFT: (2133, 667, -1, 416009, False)>

### INCENDIARY_SHIP        = <UnitInfo.INCENDIARY_SHIP: (2134, 668, -1, 416009, False)>

### HEAVY_INCENDIARY_SHIP        = <UnitInfo.HEAVY_INCENDIARY_SHIP: (2135, 669, -1, 416009, False)>

### CATAPULT_SHIP        = <UnitInfo.CATAPULT_SHIP: (2138, 671, -1, 416011, False)>

### ONAGER_SHIP        = <UnitInfo.ONAGER_SHIP: (2139, 672, -1, 416011, False)>

### LEVIATHAN        = <UnitInfo.LEVIATHAN: (2140, 670, -1, 416012, False)>

### TRANSPORT_SHIP_ANTIQUITY        = <UnitInfo.TRANSPORT_SHIP_ANTIQUITY: (2148, 655, -1, 416005, False)>

### MERCHANT_SHIP        = <UnitInfo.MERCHANT_SHIP: (2149, 660, -1, 416004, False)>

### WAR_CHARIOT_ANTIQUITY        = <UnitInfo.WAR_CHARIOT_ANTIQUITY: (2150, 627, 2302, 416015, False)>

### ELITE_WAR_CHARIOT_ANTIQUITY        = <UnitInfo.ELITE_WAR_CHARIOT_ANTIQUITY: (2151, 628, 2303, 416015, False)>

### IMMORTAL_RANGED        = <UnitInfo.IMMORTAL_RANGED: (2174, 630, 2304, 16101, False)>

### ELITE_IMMORTAL_RANGED        = <UnitInfo.ELITE_IMMORTAL_RANGED: (2175, 630, 2304, 16101, False)>

### RHODIAN_SLINGER        = <UnitInfo.RHODIAN_SLINGER: (2320, 693, 2367, 16743, False)>

### MERCENARY_HOPLITE        = <UnitInfo.MERCENARY_HOPLITE: (2321, 691, 2361, 416013, False)>

### GREEK_NOBLE_CAVALRY        = <UnitInfo.GREEK_NOBLE_CAVALRY: (2322, 684, 2369, 416016, False)>

### SCYTHIAN_AXE_CAVALRY        = <UnitInfo.SCYTHIAN_AXE_CAVALRY: (2323, 687, 2374, 416016, False)>

### BACTRIAN_ARCHER        = <UnitInfo.BACTRIAN_ARCHER: (2324, 686, 2366, 416016, False)>

### EKDROMOS        = <UnitInfo.EKDROMOS: (2325, 685, 2357, 416016, False)>

### CRETAN_ARCHER        = <UnitInfo.CRETAN_ARCHER: (2326, 683, 2365, 416016, False)>

### CAMEL_RAIDER        = <UnitInfo.CAMEL_RAIDER: (2327, 681, 2368, 16416, False)>

### TARANTINE_CAVALRY        = <UnitInfo.TARANTINE_CAVALRY: (2328, 689, 2375, 16417, False)>

### SPARABARA        = <UnitInfo.SPARABARA: (2329, 692, 2372, 16101, False)>

### SAKAN_AXEMAN        = <UnitInfo.SAKAN_AXEMAN: (2330, 688, 2358, 416016, False)>

### SICKLE_WARRIOR        = <UnitInfo.SICKLE_WARRIOR: (2331, 690, 2362, 16101, False)>

### MERCENARY_PELTAST        = <UnitInfo.MERCENARY_PELTAST: (2332, 694, 2377, 16087, False)>

### LYSANDERS_RAIDER        = <UnitInfo.LYSANDERS_RAIDER: (2349, 691, 2361, 416016, False)>

### HINT_OBJECT        = <UnitInfo.HINT_OBJECT: (2238, -1, -1, 16000, False)>

### MOUFLON        = <UnitInfo.MOUFLON: (2340, 755, 2341, 16071, True)>

### GOAT_UNCONVERTIBLE        = <UnitInfo.GOAT_UNCONVERTIBLE: (2381, 200, 1061, 16061, False)>

### MOUNTED_SAMURAI        = <UnitInfo.MOUNTED_SAMURAI: (1568, 103, 1569, 16661, False)>

### HUNNIC_HORSE        = <UnitInfo.HUNNIC_HORSE: (1869, 112, 815, 16714, False)>

### ARGALI        = <UnitInfo.ARGALI: (1896, 530, 43, 16071, True)>

### FIRE_LANCER        = <UnitInfo.FIRE_LANCER: (1901, 457, 2, 16671, False)>

### ELITE_FIRE_LANCER        = <UnitInfo.ELITE_FIRE_LANCER: (1903, 458, 2, 16671, False)>

### ROCKET_CART        = <UnitInfo.ROCKET_CART: (1904, 459, 2, 16095, False)>

### HEAVY_ROCKET_CART        = <UnitInfo.HEAVY_ROCKET_CART: (1907, 460, 2, 16095, False)>

### IRON_PAGODA        = <UnitInfo.IRON_PAGODA: (1908, 461, 2, 16101, False)>

### ELITE_IRON_PAGODA        = <UnitInfo.ELITE_IRON_PAGODA: (1910, 524, 2, 16101, False)>

### GRENADIER        = <UnitInfo.GRENADIER: (1911, 462, 2, 16743, False)>

### LIAO_DAO        = <UnitInfo.LIAO_DAO: (1920, 463, 2, 16104, False)>

### ELITE_LIAO_DAO        = <UnitInfo.ELITE_LIAO_DAO: (1922, 525, 2, 16101, False)>

### MOUNTED_TREBUCHET        = <UnitInfo.MOUNTED_TREBUCHET: (1923, 464, 2, 16734, False)>

### PAGAN_PRIEST        = <UnitInfo.PAGAN_PRIEST: (1940, 349, 1024, 16099, False)>

### PAGAN_PRIEST_WITH_RELIC        = <UnitInfo.PAGAN_PRIEST_WITH_RELIC: (1941, 349, 1024, 16380, False)>

### TRACTION_TREBUCHET        = <UnitInfo.TRACTION_TREBUCHET: (1942, 428, 2, 16093, False)>

### HEI_GUANG_CAVALRY        = <UnitInfo.HEI_GUANG_CAVALRY: (1944, 429, 1945, 16068, False)>

### HEAVY_HEI_GUANG_CAVALRY        = <UnitInfo.HEAVY_HEI_GUANG_CAVALRY: (1946, 430, 1947, 16070, False)>

### LOU_CHUAN        = <UnitInfo.LOU_CHUAN: (1948, 431, -1, 16738, False)>

### TIGER_CAVALRY        = <UnitInfo.TIGER_CAVALRY: (1949, 432, 1950, 16101, False)>

### ELITE_TIGER_CAVALRY        = <UnitInfo.ELITE_TIGER_CAVALRY: (1951, 526, 1950, 16101, False)>

### XIANBEI_RAIDER        = <UnitInfo.XIANBEI_RAIDER: (1952, 433, 1953, 16085, False)>

### DUMMY_TARGET        = <UnitInfo.DUMMY_TARGET: (1956, 337, 1956, 16061, True)>

### WHITE_FEATHER_GUARD        = <UnitInfo.WHITE_FEATHER_GUARD: (1959, 434, 1960, 16667, False)>

### ELITE_WHITE_FEATHER_GUARD        = <UnitInfo.ELITE_WHITE_FEATHER_GUARD: (1961, 527, 1960, 16101, False)>

### WAR_CHARIOT_FOCUS_FIRE        = <UnitInfo.WAR_CHARIOT_FOCUS_FIRE: (1962, 435, 2, 16096, False)>

### FIRE_ARCHER        = <UnitInfo.FIRE_ARCHER: (1968, 436, 1969, 16107, False)>

### ELITE_FIRE_ARCHER        = <UnitInfo.ELITE_FIRE_ARCHER: (1970, 528, 1969, 16101, False)>

### JIAN_SWORDSMAN        = <UnitInfo.JIAN_SWORDSMAN: (1974, 437, 1975, 16748, False)>

### JIAN_SWORDSMAN_TWO_HANDED        = <UnitInfo.JIAN_SWORDSMAN_TWO_HANDED: (1976, 438, 1977, 16748, False)>

### WAR_CHARIOT_BARRAGE        = <UnitInfo.WAR_CHARIOT_BARRAGE: (1980, 435, 2, 16417, False)>

### RED_CROWN_CRANE        = <UnitInfo.RED_CROWN_CRANE: (2026, 285, -1, 16058, True)>

### CHICKEN_A        = <UnitInfo.CHICKEN_A: (2083, 439, 595, 16061, False)>

### WILD_CHICKEN_A        = <UnitInfo.WILD_CHICKEN_A: (2084, 531, 43, 16071, True)>

### CHICKEN_B        = <UnitInfo.CHICKEN_B: (2085, 439, 595, 16061, False)>

### WILD_CHICKEN_B        = <UnitInfo.WILD_CHICKEN_B: (2086, 531, 43, 16071, True)>

### CHICKEN_C        = <UnitInfo.CHICKEN_C: (2087, 439, 595, 16061, False)>

### WILD_CHICKEN_C        = <UnitInfo.WILD_CHICKEN_C: (2088, 531, 43, 16071, True)>

### BLACK_BEAR        = <UnitInfo.BLACK_BEAR: (2089, 151, 489, 16712, True)>

### POLAR_BEAR        = <UnitInfo.POLAR_BEAR: (2090, 532, 489, 16712, True)>

### ARABIAN_WOLF        = <UnitInfo.ARABIAN_WOLF: (2091, 533, 237, 16075, True)>

### WILD_HORSE_B        = <UnitInfo.WILD_HORSE_B: (2092, 112, 815, 16735, True)>

### WILD_HORSE_C        = <UnitInfo.WILD_HORSE_C: (2093, 112, 815, 16735, True)>

### WILD_HORSE_D        = <UnitInfo.WILD_HORSE_D: (2094, 112, 815, 16735, True)>

### WILD_HORSE_E        = <UnitInfo.WILD_HORSE_E: (2095, 112, 815, 16735, True)>

### MONKEY        = <UnitInfo.MONKEY: (2096, 132, 815, 16735, True)>

### PENGUIN_GAIA        = <UnitInfo.PENGUIN_GAIA: (2097, 157, 815, 16735, True)>

### RED_FOX        = <UnitInfo.RED_FOX: (1955, 535, 43, 16075, True)>

### ARCTIC_FOX        = <UnitInfo.ARCTIC_FOX: (1958, 536, 43, 16075, True)>

### LLAMA_B        = <UnitInfo.LLAMA_B: (1963, 156, 595, 16498, False)>

### ARCTIC_WOLF        = <UnitInfo.ARCTIC_WOLF: (1965, 537, 237, 16075, True)>

### HARE_A        = <UnitInfo.HARE_A: (2098, 534, 43, 16071, True)>

### HARE_B        = <UnitInfo.HARE_B: (2099, 534, 43, 16071, True)>

### ARCTIC_HARE        = <UnitInfo.ARCTIC_HARE: (2100, 538, 43, 16071, True)>

### COMPANION_CAVALRY        = <UnitInfo.COMPANION_CAVALRY: (2382, 709, 2392, 16104, False)>

### ELITE_COMPANION_CAVALRY        = <UnitInfo.ELITE_COMPANION_CAVALRY: (2383, 709, 2392, 16104, False)>

### PHALANGITE        = <UnitInfo.PHALANGITE: (2384, 704, 2393, 416063, False)>

### ELITE_PHALANGITE        = <UnitInfo.ELITE_PHALANGITE: (2385, 704, 2393, 416063, False)>

### RHOMPHAIA_WARRIOR        = <UnitInfo.RHOMPHAIA_WARRIOR: (2386, 703, 2394, 16104, False)>

### ELITE_RHOMPHAIA_WARRIOR        = <UnitInfo.ELITE_RHOMPHAIA_WARRIOR: (2387, 703, 2394, 16104, False)>

### PATTIYODHA_LONGBOWMAN        = <UnitInfo.PATTIYODHA_LONGBOWMAN: (2388, 702, 2395, 16104, False)>

### ELITE_PATTIYODHA_LONGBOWMAN        = <UnitInfo.ELITE_PATTIYODHA_LONGBOWMAN: (2389, 702, 2395, 16104, False)>

### SANNAHYA        = <UnitInfo.SANNAHYA: (2390, 710, 2396, 416064, False)>

### ELITE_SANNAHYA        = <UnitInfo.ELITE_SANNAHYA: (2391, 710, 2396, 416064, False)>

### INDIAN_TRIBESMAN        = <UnitInfo.INDIAN_TRIBESMAN: (2449, 705, 2450, 16078, False)>

### HILL_TRIBESMAN        = <UnitInfo.HILL_TRIBESMAN: (2453, 706, 2454, 416016, False)>

### SCYTHIAN_HORSE_ARCHER        = <UnitInfo.SCYTHIAN_HORSE_ARCHER: (2485, 720, 2497, 416065, False)>

### ELITE_SCYTHIAN_HORSE_ARCHER        = <UnitInfo.ELITE_SCYTHIAN_HORSE_ARCHER: (2486, 721, 2512, 416065, False)>

### SACRED_BAND        = <UnitInfo.SACRED_BAND: (2487, 719, 2503, 416013, False)>

### OWL        = <UnitInfo.OWL: (2490, 283, -1, 16073, True)>

### PEACOCK        = <UnitInfo.PEACOCK: (2537, 756, 2538, 16733, True)>

### MOVEABLE_MAP_REVEALER_B        = <UnitInfo.MOVEABLE_MAP_REVEALER_B: (127, -1, -1, 16000, False)>

### NESSIE        = <UnitInfo.NESSIE: (1973, -1, -1, 16716, True)>

### CHAMPI_SCOUT        = <UnitInfo.CHAMPI_SCOUT: (2550, 540, 2, 16079, False)>

### INVISIBLE_OBJECT_B        = <UnitInfo.INVISIBLE_OBJECT_B: (2551, -1, -1, 16000, False)>

### CHAMPI_WARRIOR        = <UnitInfo.CHAMPI_WARRIOR: (2552, 541, 2, 16079, False)>

### INVISIBLE_OBJECT_C        = <UnitInfo.INVISIBLE_OBJECT_C: (2553, -1, -1, 16000, False)>

### ELITE_CHAMPI_WARRIOR        = <UnitInfo.ELITE_CHAMPI_WARRIOR: (2554, 542, 2, 16079, False)>

### INVISIBLE_OBJECT_D        = <UnitInfo.INVISIBLE_OBJECT_D: (2555, -1, -1, 16000, False)>

### MISSIONARY_WITH_RELIC        = <UnitInfo.MISSIONARY_WITH_RELIC: (2557, 107, 776, 16380, False)>

### GUECHA_WARRIOR        = <UnitInfo.GUECHA_WARRIOR: (2562, 543, 2, 16101, False)>

### INVISIBLE_OBJECT_E        = <UnitInfo.INVISIBLE_OBJECT_E: (2563, -1, -1, 16000, False)>

### ELITE_GUECHA_WARRIOR        = <UnitInfo.ELITE_GUECHA_WARRIOR: (2564, 544, 2, 16101, False)>

### KONA        = <UnitInfo.KONA: (2566, 545, 2, 16101, False)>

### ELITE_KONA        = <UnitInfo.ELITE_KONA: (2568, 546, 2, 16101, False)>

### BOLAS_RIDER        = <UnitInfo.BOLAS_RIDER: (2569, 547, 2, 16085, False)>

### ELITE_BOLAS_RIDER        = <UnitInfo.ELITE_BOLAS_RIDER: (2571, 548, 2, 16085, False)>

### BLACKWOOD_ARCHER        = <UnitInfo.BLACKWOOD_ARCHER: (2579, 549, 2, 16107, False)>

### ELITE_BLACKWOOD_ARCHER        = <UnitInfo.ELITE_BLACKWOOD_ARCHER: (2581, 550, 2, 16107, False)>

### IBIRAPEMA_WARRIOR        = <UnitInfo.IBIRAPEMA_WARRIOR: (2582, 551, 2, 16671, False)>

### ELITE_IBIRAPEMA_WARRIOR        = <UnitInfo.ELITE_IBIRAPEMA_WARRIOR: (2584, 552, 2, 16671, False)>

### TEMPLE_GUARD        = <UnitInfo.TEMPLE_GUARD: (2586, 553, 2, 16671, False)>

### ELITE_TEMPLE_GUARD        = <UnitInfo.ELITE_TEMPLE_GUARD: (2587, 554, 2, 16671, False)>

### CHAMPI_RUNNER        = <UnitInfo.CHAMPI_RUNNER: (2588, 555, 2, 16079, False)>

### TAPIR        = <UnitInfo.TAPIR: (2589, 557, 356, 16406, True)>

### CAPYBARA        = <UnitInfo.CAPYBARA: (2590, 558, 595, 16498, False)>

### GUANACO        = <UnitInfo.GUANACO: (2591, 559, 43, 16071, True)>

### SNAKE        = <UnitInfo.SNAKE: (2592, 560, 237, 16060, True)>

### CONDOR        = <UnitInfo.CONDOR: (2593, 568, -1, 16716, True)>

### CAIMAN        = <UnitInfo.CAIMAN: (2594, 561, 237, 16060, True)>

### BLACK_PANTHER        = <UnitInfo.BLACK_PANTHER: (2595, 562, 237, 16712, True)>

### FLAMINGO        = <UnitInfo.FLAMINGO: (2596, 563, -1, 16058, True)>

### RHEA        = <UnitInfo.RHEA: (2597, 564, 43, 16071, True)>

### WAR_DOG        = <UnitInfo.WAR_DOG: (2612, 586, 237, 16671, False)>

### ELITE_WAR_DOG        = <UnitInfo.ELITE_WAR_DOG: (2613, 587, 237, 16671, False)>

### ALPACA        = <UnitInfo.ALPACA: (2614, 589, 815, 16714, False)>

### WILD_ALPACA        = <UnitInfo.WILD_ALPACA: (2615, 589, 815, 16735, True)>

### HULK        = <UnitInfo.HULK: (2626, 566, -1, 16739, False)>

### WAR_HULK        = <UnitInfo.WAR_HULK: (2627, 565, -1, 16739, False)>

### CARRACK        = <UnitInfo.CARRACK: (2628, 567, -1, 16739, False)>

### WHALING_SHIP        = <UnitInfo.WHALING_SHIP: (2630, 24, -1, 16090, False)>

### CATAPULT_GALLEON        = <UnitInfo.CATAPULT_GALLEON: (2633, 591, -1, 16287, False)>

### TREASURE_CHEST        = <UnitInfo.TREASURE_CHEST: (2635, 295, 285, 16082, False)>

### WALRUS        = <UnitInfo.WALRUS: (1924, 936, 356, 16406, True)>

### RAVEN        = <UnitInfo.RAVEN: (2578, 934, -1, 16716, True)>

### MOUNTED_CROSSBOWMAN        = <UnitInfo.MOUNTED_CROSSBOWMAN: (2700, 900, 34, 16085, False)>

### HEAVY_MOUNTED_CROSSBOWMAN        = <UnitInfo.HEAVY_MOUNTED_CROSSBOWMAN: (2701, 901, 34, 16412, False)>

### VARANGIAN_GUARD        = <UnitInfo.VARANGIAN_GUARD: (2703, 902, 1116, 16671, False)>

### ELITE_VARANGIAN_GUARD        = <UnitInfo.ELITE_VARANGIAN_GUARD: (2704, 903, 1116, 16671, False)>

### HEARTH_TROOP        = <UnitInfo.HEARTH_TROOP: (2705, 904, 2, 16101, False)>

### ELITE_HEARTH_TROOP        = <UnitInfo.ELITE_HEARTH_TROOP: (2706, 905, 2, 16101, False)>

### JARL        = <UnitInfo.JARL: (2708, 906, 1628, 16101, False)>

### ELITE_JARL        = <UnitInfo.ELITE_JARL: (2709, 907, 1628, 16101, False)>

### JOMSVIKING        = <UnitInfo.JOMSVIKING: (2711, 908, 2, 16101, False)>

### ELITE_JOMSVIKING        = <UnitInfo.ELITE_JOMSVIKING: (2712, 909, 2, 16101, False)>

### REPAIRER_MALE        = <UnitInfo.REPAIRER_MALE: (2714, 330, 225, 16127, False)>

### REPAIRER_FEMALE        = <UnitInfo.REPAIRER_FEMALE: (2715, 329, 225, 16127, False)>

### WHEELED_SHIP        = <UnitInfo.WHEELED_SHIP: (2730, 40, 435, 16301, False)>

### SEAL        = <UnitInfo.SEAL: (2735, 935, 43, 16071, True)>

### LYNX        = <UnitInfo.LYNX: (2736, 932, 237, 16075, True)>

### ELK        = <UnitInfo.ELK: (2737, 931, 356, 16406, True)>

### PHEASANT        = <UnitInfo.PHEASANT: (2739, 933, 43, 16071, True)>

### FLAMING_BIRD        = <UnitInfo.FLAMING_BIRD: (2742, 283, -1, 16058, True)>


---

## 附录 A：页面清单与体量

| 页面 | HTML 字节 | MD 字符 |
|---|---|---|
| `api/AoE2ScenarioParser/objects/support/new_effect.html` | 2033581 | 33944 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/attribute.html` | 1514130 | 91443 |
| `api/AoE2ScenarioParser/datasets/techs.html` | 1171923 | 45173 |
| `api/AoE2ScenarioParser/datasets/units.html` | 1058381 | 45561 |
| `api/AoE2ScenarioParser/objects/support/area.html` | 774311 | 15623 |
| `api/AoE2ScenarioParser/objects/managers/trigger_manager.html` | 718947 | 15026 |
| `api/AoE2ScenarioParser/datasets/other.html` | 691026 | 32148 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/object_attribute.html` | 632338 | 43507 |
| `api/AoE2ScenarioParser/objects/support/new_condition.html` | 540665 | 8452 |
| `api/AoE2ScenarioParser/objects/data_objects/effect.html` | 494790 | 5557 |
| `api/AoE2ScenarioParser/scenarios/aoe2_scenario.html` | 457940 | 5488 |
| `api/AoE2ScenarioParser/datasets/effects.html` | 440689 | 27231 |
| `api/AoE2ScenarioParser/datasets/heroes.html` | 420113 | 21319 |
| `api/AoE2ScenarioParser/datasets/buildings.html` | 409376 | 22858 |
| `api/AoE2ScenarioParser/objects/managers/unit_manager.html` | 386356 | 10171 |
| `api/AoE2ScenarioParser/datasets/projectiles.html` | 340789 | 14735 |
| `api/AoE2ScenarioParser/objects/data_objects/trigger.html` | 328970 | 4094 |
| `api/AoE2ScenarioParser/objects/managers/player_manager.html` | 325321 | 2693 |
| `api/AoE2ScenarioParser/objects/data_objects/player/player.html` | 229025 | 2929 |
| `api/AoE2ScenarioParser/objects/managers/map_manager.html` | 222746 | 3161 |
| `api/AoE2ScenarioParser/datasets/terrains.html` | 222059 | 8422 |
| `api/AoE2ScenarioParser/objects/support/xs_check.html` | 206589 | 2115 |
| `api/AoE2ScenarioParser/objects/data_objects/condition.html` | 192747 | 2446 |
| `api/AoE2ScenarioParser/datasets/object_support.html` | 188855 | 8470 |
| `api/AoE2ScenarioParser/objects/managers/xs_manager.html` | 184829 | 1862 |
| `api/AoE2ScenarioParser/datasets/conditions.html` | 181954 | 8582 |
| `api/AoE2ScenarioParser/datasets/support/info_dataset_base.html` | 142349 | 1567 |
| `api/AoE2ScenarioParser/objects/data_objects/unit.html` | 120484 | 1310 |
| `api/AoE2ScenarioParser/scenarios/aoe2_de_scenario.html` | 119320 | 1800 |
| `api/AoE2ScenarioParser/datasets/players.html` | 105624 | 2548 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/object_class.html` | 102084 | 3731 |
| `api/AoE2ScenarioParser/objects/managers/option_manager.html` | 98502 | 1061 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/hero_status_flag.html` | 96903 | 2303 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/damage_class.html` | 94588 | 3735 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/hotkey.html` | 90916 | 2640 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/terrain_restrictions.html` | 84754 | 3391 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/button_location.html` | 81685 | 1742 |
| `api/AoE2ScenarioParser/objects/managers/message_manager.html` | 80943 | 787 |
| `api/AoE2ScenarioParser/objects/data_objects/terrain_tile.html` | 78455 | 654 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/unit_ai_action.html` | 76188 | 2266 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/action_type.html` | 72656 | 2000 |
| `api/AoE2ScenarioParser/objects/support/trigger_ce_lock.html` | 66829 | 927 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/secondary_game_mode.html` | 66651 | 936 |
| `api/AoE2ScenarioParser/objects/support/trigger_select.html` | 64998 | 1181 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/color_mood.html` | 58930 | 1136 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/blast_level.html` | 57097 | 1176 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/charge_type.html` | 54419 | 1155 |
| `api/AoE2ScenarioParser/datasets/scenario_variant.html` | 54199 | 425 |
| `api/AoE2ScenarioParser/objects/support/tile.html` | 53234 | 891 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/obstruction_type.html` | 52888 | 1130 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/combat_ability.html` | 51889 | 1027 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/comparison.html` | 51374 | 812 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/technology_state.html` | 50704 | 954 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/object_state.html` | 50493 | 777 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/occlusion_mode.html` | 50311 | 857 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/local_technology.html` | 49999 | 965 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/blockage_class.html` | 49888 | 727 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/garrison_type.html` | 49632 | 733 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/difficulty_level.html` | 49475 | 772 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/projectile_hit_mode.html` | 48560 | 718 |
| `api/AoE2ScenarioParser/objects/data_objects/variable.html` | 48471 | 238 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/victory_condition.html` | 48242 | 667 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/selection_effect.html` | 47893 | 652 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/fog_visibility.html` | 47408 | 676 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/time_unit.html` | 47142 | 589 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/capture_flag.html` | 46833 | 565 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/unit_trait.html` | 46748 | 588 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/operation.html` | 46635 | 582 |
| `api/AoE2ScenarioParser/settings.html` | 46607 | 1652 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/charge_event.html` | 46604 | 633 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/panel_location.html` | 46389 | 607 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/projectile_smart_mode.html` | 46239 | 660 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/attack_stance.html` | 46187 | 557 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/projectile_vanish_mode.html` | 46069 | 608 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/object_modify_attribute_state.html` | 46008 | 514 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/disable_unit_flag.html` | 45775 | 616 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/object_type.html` | 45721 | 509 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/attack_priority.html` | 45615 | 566 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/visibility_state.html` | 45330 | 522 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/age.html` | 45234 | 469 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/victory_timer_type.html` | 45109 | 474 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/diplomacy_state.html` | 45054 | 469 |
| `api/AoE2ScenarioParser/datasets/trigger_lists/decision_option.html` | 43701 | 342 |
| `api/index.html` | 43431 | 48 |

## 附录 B：复跑

```bash
# 1) 抓全 84 页 pdoc（trust_env=False 绕本机代理）
python -X utf8 _probe/_tmp/asp_crawl.py
# 2) HTML -> Markdown（strip pdoc-code 后按 section/classattr 切块）
python -X utf8 _probe/_tmp/asp_parse2.py
# 3) 生成本卷
python -X utf8 _probe/_tmp/gen_vol24.py
```

## 附录 C：pdoc 解析的两个坑

1. **成员不在 `<section>` 里，在 `<div id="X.Y" class="classattr">`**。只按 `<section id=` 找只能拿到 1 个类头，613 个枚举成员全部丢失（第一版 30,886 字符 vs 修好后 545,647 字符）。
2. **`View Source` 代码块必须删**。`<div class="pdoc-code codehilite">` 里是带行号 span 的源码，不删会混进正文，且 `</div>` 嵌套需要配平计数，不能正则一刀切。

## 附录 D：`_asp_enums.csv`（3932 条枚举导出）

从本卷正文用 `^### (\w+)\s+= <(\w+)\.(\w+): (.*)>$` 抽出，只保留 `member == name` 的真成员行（排除 `class X` 头与重复的 `= ~S` 类型变量），去重后 3932 条。

字段：`enum,member,id,icon_id,line`。`id` 是游戏内 ID（用于 `.aoe2scenario` 的 dataset 字段），`icon_id` 是图标索引（多数枚举没有，留空）。

| enum | 条数 | 用途 |
|---|---|---|
| `Attribute` | 601 | 单位/建筑属性（effect 的 attribute 参数）；注意与 07 卷的 XS 属性 ID **不是同一套编号** |
| `TechInfo` | 600 | 科技 ID + 图标 ID，`(22, 6)` 就是 Loom |
| `UnitInfo` | 518 | 单位 ID + 图标 ID |
| `OtherInfo` | 397 | 杂项对象（树/矿/遗迹等） |
| `HeroInfo` | 252 | 英雄与战役单位 |
| `BuildingInfo` | 243 | 建筑 |
| `ObjectAttribute` | 211 | trigger 里的 object attribute 枚举 |
| `ProjectileInfo` | 161 | 抛射物 |
| `TerrainId` | 134 | 地形 |
| `EffectId` | 103 | effect 类型（`SEND_CHAT=3`、`RESEARCH_TECHNOLOGY=2`…） |
| `Civilization` | 67 | 文明（含新 DLC） |
| `ObjectClass` | 64 | 护甲/攻击类 |

用法：`TechInfo.LOOM = (22, 6)` → `new_effect.research_technology(technology=22)`；`EffectId.SEND_CHAT = 3` → `new_effect.send_chat(message='hi')`。
