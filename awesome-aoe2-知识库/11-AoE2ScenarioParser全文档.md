# AoE2ScenarioParser 全文档（0.9.9）

> 出处：<https://ksneijders.github.io/AoE2ScenarioParser/>（docsify；正文取自其 `_sidebar.md` 指向的原始 Markdown 源文件）  
> 仓库：<https://github.com/KSneijders/AoE2ScenarioParser>（105★，GPL-3.0，2026-11-05）  
> 安装：`pip install AoE2ScenarioParser`  
> 抓取：2026-11-08，18 个页面全量，无删节。

---



---

# 快速开始


# Quick Start

## Installation

Install using **pip**:

```bash
pip install AoE2ScenarioParser
```

Requires **Python 3.8** or newer. Dependencies install automatically.

To update an existing installation:

```bash
pip install --no-cache-dir --upgrade AoE2ScenarioParser
```

---

## Reading a scenario

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

scenario = AoE2DEScenario.from_file("path/to/your/scenario.aoe2scenario")
```

> [!TIP]
> Your scenario files are usually found at:
> `C:\Users\<USERNAME>\Games\Age of Empires 2 DE\<STEAMID>\resources\_common\scenario`

---

## Making changes

All edits are made through **managers**. Each manager handles a different part of the scenario:

```py
trigger_manager = scenario.trigger_manager
unit_manager    = scenario.unit_manager
map_manager     = scenario.map_manager
player_manager  = scenario.player_manager
# etc.
```

For a full overview of what each manager can do, see the Cheatsheets.

---

## Writing a scenario

> [!WARNING]
> Always write to a **different file** than your input. Overwriting your source scenario can cause data loss in case of bugs or mistakes.

```py
scenario.write_to_file("path/to/your/output.aoe2scenario")
```

---

For a step-by-step walkthrough with examples, see the [Hello World](hello_world.md) guide.


---

# Hello World


# Hello World Example

## Introduction

Now that you've installed `AoE2ScenarioParser`, let's do some simple editing!

We'll read a scenario, add a trigger, some units and edit some terrain and write it back to a new scenario.

This "hello world" example assumes you've installed an editor.  
A great editor (IDE) is PyCharm: [Download PyCharm]

## Step by step

### 1. Create the scenario

Create an empty scenario in the editor and save it as "hello world"

### 2. Set up the project

Create a new project and file (in PyCharm). Name the file `hello_world.py`, and copy the code below into `hello_world.py`

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

# The path to your scenario folder
input_folder = "C:/path/to/your/scenario/folder/"

# The scenario object. 
scenario = AoE2DEScenario.from_file(input_folder + "hello world.aoe2scenario")
```

### 3. Getting the scenario path

1. Go to the "Load Scenario" menu in-game (Single Player → Editors)
2. Copy the path that is opened when clicking the "Open Scenario Folder" button (Bottom right)
3. Paste the folder path in the input_folder string

    > [!TIP]
    > **Folder separators**  
    > If you use `\` to separate folders, use 2 per folder (`c:\\folder\\folder\\`)  
    > If you use `/` to separate folders, 1 is enough (`c:/folder/folder/`)  

4. Remember to add a `/` or `\\` at the end of the string too

### 4. Test if it works

Run the python code by pressing `CTRL` + `SHIFT` + `F10`

> [!TIP] `CTRL` + `SHIFT` + `F10` executes the current file in PyCharm. [More info here](https://www.jetbrains.com/help/pycharm/creating-and-running-your-first-python-project.html#run).

You should get a console output that looks like this:

```md
Reading file: 'YOUR FILE PATH' 
Reading scenario file finished successfully.
############### Attributes ###############
>>> Game version: 'DE'
>>> Scenario version: 1.43
##########################################
Loading scenario structure finished successfully.
Parsing scenario file...
    ✔ FileHeader
    ✔ DataHeader
...
```

### 5. Adding a trigger

Now let's add a trigger with a `Display Instructions` effect that reads "Hello World"

1. Add the following code to `hello_world.py`

    ```py
    # Save reference to the manager, so you don't have to do "scenario.trigger_manager..." each time
    trigger_manager = scenario.trigger_manager

    # Save the created trigger
    hello_world_trigger = trigger_manager.add_trigger("Hello World Trigger")
    # Add display_instructions effect to the new trigger
    hello_world_trigger.new_effect.display_instructions(
        display_time=11,
        message="Hello World"
    )
    ```

2.  Now let's check it out in game. Add the following code:

    ```py
    scenario.write_to_file(input_folder + "hello world output.aoe2scenario")
    ```

    This will save the changes made to the scenario to a new file specified at the given path. 

3.  Run the python code by pressing `SHIFT` + `F10` (rerun the last file)
4.  You should see something like this at the end of your console:

    ```
    ...
        ✔ Triggers
        ✔ Files
    File writing finished successfully.
    File successfully written to: 'YOUR OUTPUT FILE PATH'
    Process finished with exit code 0
    ```

5.  Check out the "hello world output" scenario in-game and test it!

### 6. Adding units

1. Remove the `scenario.write_to_file(...)` line, we'll add it back later
2. Let's add the `unit_manager` to the script where we added the trigger manager:

    ```py
    unit_manager = scenario.unit_manager
    ```

3. Now let's add the code to add some units to the end of the script:

    ```py
    unit_manager.add_unit(player=Player.ONE, unit_const=UnitInfo.MILITIA.ID,              x=15, y=12)
    unit_manager.add_unit(player=Player.ONE, unit_const=UnitInfo.MAN_AT_ARMS.ID,          x=15, y=13)
    unit_manager.add_unit(player=Player.ONE, unit_const=UnitInfo.LONG_SWORDSMAN.ID,       x=15, y=14)
    unit_manager.add_unit(player=Player.ONE, unit_const=UnitInfo.TWO_HANDED_SWORDSMAN.ID, x=15, y=15)
    unit_manager.add_unit(player=Player.ONE, unit_const=UnitInfo.CHAMPION.ID,             x=15, y=16)
    ```

    Take a look at the code, maybe you can see what it does?

4. We add one unit per unit from the militia line to the editor, one per tile.

    > [!NOTE]
    > These units are placed using whole numbers (called: integers, `x=15, y=12`), if you want units to spawn in the middle of a tile, use
    > `.5` after the integer, like so: `x=15.5, y=12.5`  

5. You can also see the above code uses `Player` and `UnitInfo` objects.

    ```
    Player.ONE         # The number representing player one (1)
    UnitInfo.MILITIA.ID  # The number representing a militia unit (74)
    ```

    > [!NOTE]
    > **Datasets**  
    > These are datasets, A Dataset is an Enum Class that contains the constants used by the game like unit IDs, etc. These are essential to producing a scenario. Read more about them [here](cheatsheets/datasets.md).

6. Let's import the datasets using the code below. Add these lines to the top of your file.

    ```py
    from AoE2ScenarioParser.datasets.player_data import Player
    from AoE2ScenarioParser.datasets.units import UnitInfo
    ```

### 7. Changing the map

1. And now as a final change, let's add a hill and change the size of the map. First get the `map_manager`:

    ```py
    map_manager = scenario.map_manager
    ```
    Place it with the `unit_manager` and the `trigger_manager`

2. Now let's add the code for the hill:

    ```py
    map_manager.set_elevation(elevation=1, x1=3, y1=6, x2=9, y2=12)
    ```

    The in-game max elevation is 7, that's equivelant to `elevation=6` in the parser.
    This is because `elevation=0` is elevation 1 in the editor.
    Using the parser you can go as large as you want, though the game can bug out if you go above 20.

    Below is a graphic explaining how the map coordinates work:

    ![](images/map_coordinates_explained.png)
    Thanks to [ScribbleGhost](https://github.com/ScribbleGhost) for the graphic! ❤️

3. And finally let's shrink the map size to `40x40` tiles

    ```py
    map_manager.map_size = 40
    ```

    > [!WARNING]
    > **Max map size limit**  
    > The limit of a scenario is set to the size of a ludikrous map (`480x480`).  
    > Going over this limit will cause the game to crash.

4. Now let's add the writing to file back:

    ```py
    scenario.write_to_file(input_folder + "hello world output.aoe2scenario")
    ```

5. Run the python code by pressing `SHIFT` + `F10` again and check out the scenario!


## Complete code block

Your code should look something like the below block. You can find more examples & explanation on the
[cheatsheets](cheatsheets/triggers.md) and the
[examples](examples/triggers.md) page.

```py
from AoE2ScenarioParser.datasets.player_data import Player
from AoE2ScenarioParser.datasets.units import UnitInfo
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

# The path to your scenario folder
input_folder = "C:/path/to/your/scenario/folder/"

# The scenario object.
scenario = AoE2DEScenario.from_file(input_folder + "hello world.aoe2scenario")

# Save reference to the manager, so you don't have to do "scenario.trigger_manager..." each time
trigger_manager = scenario.trigger_manager
unit_manager = scenario.unit_manager
map_manager = scenario.map_manager

# Save the created trigger
hello_world_trigger = trigger_manager.add_trigger("Hello World Trigger")
# Add display_instructions effect to the new trigger
hello_world_trigger.new_effect.display_instructions(
    display_time=11,
    message="Hello World"
)

unit_manager.add_unit(player=Player.ONE, unit_const=UnitInfo.MILITIA.ID, x=15, y=12)
unit_manager.add_unit(player=Player.ONE, unit_const=UnitInfo.MAN_AT_ARMS.ID, x=15, y=13)
unit_manager.add_unit(player=Player.ONE, unit_const=UnitInfo.LONG_SWORDSMAN.ID, x=15, y=14)
unit_manager.add_unit(player=Player.ONE, unit_const=UnitInfo.TWO_HANDED_SWORDSMAN.ID, x=15, y=15)
unit_manager.add_unit(player=Player.ONE, unit_const=UnitInfo.CHAMPION.ID, x=15, y=16)

map_manager.set_elevation(elevation=1, x1=3, y1=6, x2=9, y2=12)
map_manager.map_size = 40

scenario.write_to_file(input_folder + "hello world output.aoe2scenario")
```

[Download PyCharm]: https://www.jetbrains.com/pycharm/download/


---

# 触发器 Trigger


# Triggers

You can use the trigger manager to add, remove edit and view triggers
and variables.

## Adding

Here's an example of how to create (add) a trigger and add a condition
and effect to it:

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.units import UnitInfo

# File & Folder setup
# Define paths to the scenario folder.
# You can find this folder by opening AoE2:DE and going to scenarios and clicking on 'open folder'
scenario_folder = "your/path/to/the/scenario/folder/"  # <-- Final slash is important
scenario_name = "name_of_your_scenario"

# Define Scenario file
scenario = AoE2DEScenario.from_file(f"{scenario_folder}{scenario_name}.aoe2scenario")

# Add Trigger
trigger_manager = scenario.trigger_manager
trigger = trigger_manager.add_trigger("Trigger Name Here")

# Add Timer Condition
timer_condition = trigger.new_condition.timer(timer=20)

# Add Create Object Effect
create_paladin_effect = trigger.new_effect.create_object(
    object_list_unit_id=UnitInfo.PALADIN.ID,
    source_player=PlayerId.ONE,
    location_x=5,
    location_y=4,
)

# Write to same folder with name + '_output'
scenario.write_to_file(f"{scenario_folder}{scenario_name}_output.aoe2scenario")
```

### Importing

Instead of directly adding triggers you can also import triggers from another scenario:

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

# Define Scenario files
source_scenario = AoE2DEScenario.from_file(path_to_the_source_file)
target_scenario = AoE2DEScenario.from_file(path_to_the_target_file)

# Define Trigger Managers
source_trigger_manager = source_scenario.trigger_manager
target_trigger_manager = target_scenario.trigger_manager

# Import the triggers
# In this case all triggers from the source scenario are copied
# You can optionally set the index to which the imported triggers are set at
# Leaving this out will add the imported triggers to the end of the target scenario
# In the example below, the source triggers will be added BEFORE the target triggers due to the 0
target_trigger_manager.import_triggers(source_trigger_manager.triggers, 0)

target_scenario.write_to_file(path_to_output_file)
```

## Selecting

Selecting a trigger can be done using the `get_trigger` function. The
function accepts 1 argument, a `TriggerSelect` (Alias: `TS`) object.  

> [!TIP]
> **For an index, just use an integer**  
> Instead of `TS.index(4)` you can just use `4`. 
> Integers are used in the same way as `TS.index(4)` for ease of use


You can import `TS` (or `TriggerSelect`) like so:

```py
from AoE2ScenarioParser.objects.support.trigger_select import TS
from AoE2ScenarioParser.objects.support.trigger_select import TriggerSelect
```

The constructor of `TriggerSelect` accepts 3 arguments, `trigger_index`,
`display_index` and `trigger`.

-   The `trigger_index` expects the trigger
    ID of a trigger. This is the a number related to the order of creation
    starting from 0.
-   The `display_index` expects the display ID of a
    trigger. This is the a number related to the display order in the
    in-game editor.
-   The `trigger` expects a trigger object. Read further
    below on how to create or select one.

```py
TriggerSelect(trigger_index=...)
TriggerSelect(display_index=...)
TriggerSelect(trigger=...)

# Use TS as alias & class methods:
TS.index(...)  # Short hand for: trigger_index
TS.display(...)  # Short hand for: display_index
TS.trigger(...)

# Examples:
trigger = trigger_manager.get_trigger(TS.index(7))
trigger = trigger_manager.get_trigger(7)  # <-- Same result as above, defaults to `TS.index(...)`
trigger = trigger_manager.get_trigger(TS.display(3))
```

You can use the `get_summary_as_string` function to view these values without opening
the in-game editor. The code below includes the code above:

```py
print(trigger_manager.get_summary_as_string())

# Results in:
"""
Trigger Summary:
    Trigger Name Here    [Index: 0, Display: 0] (conditions: 1,  effects: 1)

Variables Summary:
    << No Variables >>
"""
```

As you can see, the trigger and display index can be seen in the
`[Index: x, Display: x]` part. These are the numbers you can use to
select triggers. Which would look like:

```py
# Define Scenario file
scenario = AoE2DEScenario.from_file(read_file)

# Get Trigger
trigger_manager = scenario.trigger_manager
trigger = trigger_manager.get_trigger(0)
```

If you want to see the contents of the trigger you can do so by running
the `get_content_as_string` function. This will result in the following
(with the `create trigger` code):

```py
print(trigger_manager.get_content_as_string())

# Results in:
"""
Triggers:
    'Trigger Name Here' [Index: 0, Display: 0]:
        enabled: True
        looping: False
        conditions:
            timer [Index: 0, Display: 0]:
                timer: 20
                inverted: 0
        effects:
            create_object [Index: 0, Display: 0]:
                object_list_unit_id: UnitInfo.PALADIN.ID
                source_player: PlayerId.ONE
                location_x: 5
                location_y: 4
                facet: 0

Variables:
    <<No Variables>>
"""
```

## Editing

When opening a file that already contains triggers you might want to
edit or even remove said triggers.

You can edit a trigger like so:

```py
# Get the trigger_index or display_index using the content or summary methods above
trigger = trigger_manager.get_trigger(0)  # Or: TS.index(0)
trigger = trigger_manager.get_trigger(TS.display(0))

trigger.name = "New Trigger Name"
trigger.description = "Awesome New Description!"
```

### Copy

Pretty simple and straigtforward. It copies a trigger adding it at the
end of the trigger list. Selecting a trigger is done using the standard
trigger_index, display_index and trigger reference. You can use it as
follows:

```py
copied_trigger = trigger_manager.copy_trigger(3)
```

This will result in a full (deep)copy of your trigger. The only parts
that are edited are its `id` and the name (added `" (copy)"`).

### Copy per player

Just like the `copy_trigger` function, this trigger makes a (deep) copy
of the given function. But, while copying, it'll change the everything
player related. With this function comes great control. Below the usage
is shown:

```py
copied_triggers = trigger_manager.copy_trigger_per_player(
    from_player=PlayerId.ONE,
    trigger_select=3,
    create_copy_for_players=[
        PlayerId.TWO, PlayerId.THREE, PlayerId.FOUR  # Optional list
    ]
)
print(f"New trigger for Player Two: {copied_triggers[PlayerId.TWO]}")
```

### Copy tree

This function copies the given trigger and all that are linked to this
one. The function searches all effects in the given trigger and selects
all triggers linked to it. It gets all triggers by taking the ids from
`(de)activate trigger` effects. This will result in the entire tree being
copied:

```py
trigger_manager.copy_trigger_tree(3)
```

### Copy tree per player

A combination of the `copy_trigger_per_player` and `copy_trigger_tree`
functions. This function copies the entire tree per player. Besides the
parameters that can be given to `copy_trigger_per_player` function, an
additional `group_triggers_by` parameter is included. This way you can
select in which order all the new triggers should be placed:

```py
trigger_manager.copy_trigger_tree_per_player(
    from_player=PlayerId.ONE,
    trigger_select=3,  # Or: TS.index(3)
    group_triggers_by=GroupBy.PLAYER,  # Other options: GroupBy.NONE and GroupBy.TRIGGER
)
```

## Removing

When removing a trigger you can select it the same way as when getting a
trigger using the get_trigger function. But on top of that
you can also use it's reference:

```py
trigger_manager.remove_trigger(3)  # Or: TS.index(3)
trigger_manager.remove_trigger(TS.display(0))
trigger_manager.remove_trigger(TS.trigger(trigger))
```

For removing effects and conditions it's very similiar but the
functions are accessed from the triggers themselves instead of the
trigger_manager. You can select the effect or condition you want to
remove using:

-   it's index (the order by time of creation)
-   display index (the order like the in-game editor)
-   reference (the reference to that effect/condition object)

```py
trigger = trigger_manager.get_trigger(0)
trigger.remove_effect(effect_index=0)
trigger.remove_effect(display_index=1)
trigger.remove_effect(effect=effect)

trigger.remove_condition(condition_index=0)
trigger.remove_condition(display_index=1)
trigger.remove_condition(condition=condition)
```


---

# 数据触发器 Data Trigger


# Data Triggers

**Data Triggers** is a new feature to the parser. 
They allow you to transfer the power of visuals from the in-game editor into the parser!

## What are these data triggers?

Data triggers are basically triggers with specifically set names.  
The triggers also have some effects and conditions which selects stuff like: areas, units, triggers or tiles.

## Why do I need them?

If you ever wanted to do something with an area or specific objects or triggers that are already present in the
scenario before reading with the parser, you'd need to select them through their coordinates or names etc. This can be a
bit of a challenge or annoying to keep doing over and over at best.

So, that's what data triggers are for. You use conditions and effects to select those aspects of the map and in the 
parser you can use a simple, single line of code to get all this data easily accessible to you.

## Creating the data triggers

So, how do we create the data triggers? Well, like so:

1. Open your scenario in-game
2. Create a trigger
3. Change the name of the trigger to "_area:cool_middle_area_"
4. Create a `Bring Object to Area` conditions. (It doesn't matter which condition or effect you choose. As long as an area can be selected with it)
5. Use the `Set Area` button to select an area on the map
6. Save the scenario
7. Use the parser to load the map
8. Use the code below to get the area object:

```py
scenario = ... # Load scenario stuff here

trigger_data = scenario.actions.load_data_triggers()
cool_area = trigger_data.areas['cool_middle_area']
```

And that's it! Now you have a list of `Area` objects which contains all the areas that you selected in the trigger!
You can add more effects/conditions with areas to that trigger, and they'll be added to the list. 
You can also create another trigger with the same `area:<name>` name and add more effects or conditions to it to create 
different selections.

> [!NOTE]
> **The data triggers are automatically removed**  
> The function `.load_data_triggers()` automatically removes all triggers it finds with the proper prefix. If you'd
> like to keep these triggers you can use the `remove_template_triggers` parameter and set it to `False`.


## Different data types

Currently, there's 4 data types you can use to select information on the map. These are:

### Area

Create an `Area` object based on an area selected using the `Set Area` button in-game (Effects & Conditions).

### Tile

Create `Tile` objects based on a single tile selected using the `Set Location` button (Effects)
or a bunch of tiles selected using the `Set Area` button (Effects and Conditions) in-game.

### Object

Select a `Unit` object (or multiple `Unit` objects) based on the selected units using the `Set objects` button
(Effects and Conditions) or `Set location` button (Effects) (Works with both selecting a unit AND the tile a unit is 
standing on). It also allows selecting an area using the `Set Area` button (Effects and Conditions) and all units
within that area will be included.

### Trigger

Select a `Trigger` object based on the selected trigger in (de)activation effects using the `Trigger List` dropdown.

## Mechanics

The `load_data_triggers()` function looks for a specific prefix in the trigger names. The prefixes are as follows:

| Type      | Prefixes                    |
| --------- | --------------------------- |
| `Area`    | "_area:_", "_areas:_"       |
| `Tile`    | "_tile:_", "_tiles:_"       |
| `Object`  | "_object:_", "_objects:_"   |
| `Trigger` | "_trigger:_", "_triggers:_" |

When it finds a prefix it uses the name after the colon to store the objects in a dictionary, so these _should_ be 
unique per data type.

The function then goes through all the effects and conditions within the trigger. The effect or condition type doesn't 
matter. The function just checks the proper attributes (for example: the `area_x1`, `area_y1`, `area_x2` & `area_y2` 
attributes) for the area data type. If all of those attributes are set, it creates/finds the proper object accordingly.

The object returned by `load_data_triggers()` has 4 attributes which will return the corresponding dictionaries.
So, for example, you could store the dicts directly like so:

```py
from typing import List

from AoE2ScenarioParser.helper.attr_dict import AttrDict

from AoE2ScenarioParser.objects.data_objects.trigger import Trigger
from AoE2ScenarioParser.objects.data_objects.unit import Unit
from AoE2ScenarioParser.objects.support.area import Area
from AoE2ScenarioParser.objects.support.tile import Tile

scenario = ... # Load scenario stuff here

trigger_data = scenario.actions.load_data_triggers()

# You could leave out the 'AttrDict[...]' parts (and the corresponding imports). 
# That being said, they do help your IDE understand the proper types for type hinting later on
areas: AttrDict[str, List[Area]] = trigger_data.areas
tiles: AttrDict[str, List[Tile]] = trigger_data.tiles
triggers: AttrDict[str, List[Trigger]] = trigger_data.triggers
objects: AttrDict[str, List[Unit]] = trigger_data.objects
```

The dictionaries are also special in that they allow attribute access instead of only key access.
So to get the key "_TCs_" you can use either of these with the same result: 

```py
trigger_data.objects['TCs']
trigger_data.objects.TCs
```

> [!NOTE]
> **Keys with spaces won't work with attribute access**  
> When your key has characters like spaces (or other special chars) you have to use: 
> ```py
> trigger_data.objects['name with space here']
> ```


## Examples

### Area

This trigger was made to make an area object around berries. (Don't ask why).
You can see multiple conditions in the list. 
All of them have an area selected so the list for the `berries` will have 6 `Area` objects

![Data Trigger - Area Example](../images/data_trigger_area_example.png "Data triggers example with area selected")

### Tile

This trigger just selects a bunch of tiles. As you can see in the image, tiles can also be selected by the `Set Area`
button. This will result in multiple `Tile` objects being created for one effect. The list for this trigger will return
at least the 7 `Tile` objects selected by this condition.

![Data Trigger - Tile Example](../images/data_trigger_tile_example.png "Data triggers example with tile selected")

### Object

This trigger was made to easily select the 'main army' of a player.
The `Set Objects` button was used to select multiple units at once. 
As you can see multiple effects and conditions were used in this trigger. 
All of them have units selected through the `Set Objects` or `Set Location` buttons. 
This list will be longer than just 3 `Unit` objects as the shown effect already selects 3 units on its own. 
So, if the other 2 only selected 1 unit each, the list would have 5 `Unit` objects in total.

![Data Trigger - Object Example](../images/data_trigger_object_example.png "Data triggers example with object selected")

### Trigger

This trigger selects 2 triggers with the name 'main'. Data triggers for selecting triggers is the simplest as you can
only select 1 Trigger per effect. So this list will have 2 triggers in it.

![Data Trigger - Trigger Example](../images/data_trigger_trigger_example.png "Data triggers example with trigger selected")


---

# 单位 Units


# Units

You can use the unit manager to add, edit and remove units. This
includes buildings and heroes etc.

## Adding

Below you can find examples on how to add units to the scenario. This
will add a conquistador for player 1 at (0, 0) which is the West corner
of the map:


```py
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.units import UnitInfo

# ... 
# Read scenario etc.
# ...

# Add Unit
unit_manager = scenario.unit_manager

unit = unit_manager.add_unit(
    player=PlayerId.ONE,
    unit_const=UnitInfo.CONQUISTADOR.ID,  # Units dataset
    x=0.5,
    y=0.5
)

# Or, with more detail:
unit = unit_manager.add_unit(
    player=PlayerId.ONE,
    unit_const=UnitInfo.CONQUISTADOR.ID,
    x=0.5,
    y=0.5,
    z=0,                # The 'height' of the unit. 
    rotation=0,         # Rotation in radians
    animation_frame=0,  # The nth animation frame
)
```

## Selecting

To select the units you want there are a couple options. You can select
all the units from a certain player:

```py
gaia_units = unit_manager.get_player_units(PlayerId.GAIA)
```

Or, get all units:

```py
all_units = unit_manager.get_all_units()
```

If you want a more specific search, you can use the `get_units_in_area`
function. This function is quite powerful. You can select an area using
coordinates or using tiles. You can also use a whitelist of players or a
blacklist of players to (not) select the units from. And, if you have,
hand it your own list of units to filter through. You can see a couple
examples below:

```py
unit_manager.get_units_in_area(x1=0, y1=0, x2=10, y2=10)
# Any unit within 0,0 => 10,10

unit_manager.get_units_in_area(tile1=Tile(0, 0), tile2=Tile(10, 10))
# Any unit within 0,0 => 11, 11 (Note the 11, 11)
# This is because Tiles are squares (1x1). So: 
# >>> Tile(0,0).x1 == 0
# >>> Tile(0,0).x2 == 1
```

For all other examples we'll be using the ``[x, y]`` notation. But you can use the ``Tile`` notation interchangeably:

```py
unit_manager.get_units_in_area(x1=2, y1=3, x2=4, y2=5, players=[
    PlayerId.ONE, PlayerId.TWO
])
# Any unit within 2,3 => 4,5 from Player 1 and 2.

unit_manager.get_units_in_area(x1=2, y1=3, x2=4, y2=5, ignore_players=[
    PlayerId.GAIA
])
# Any unit within 2,3 => 4,5 from any Player but GAIA.

unit = unit_manager.add_unit(player=PlayerId.ONE, unit_const=UnitInfo.CONQUISTADOR.ID, x=5, y=1)
unit2 = unit_manager.add_unit(player=PlayerId.TWO, unit_const=UnitInfo.CONQUISTADOR.ID, x=1, y=5)

unit_manager.get_units_in_area(x1=0, y1=0, x2=9, y2=9, unit_list=[unit, unit2], players=[PlayerId.ONE])
# Selects any unit from the given list that belongs to Player 1 within 0,0 => 9,9.
```

You can also filter certain units based on their `unit_const` value.  
For this you can use the `filter_units_by_const` function.

```py
# Get TC object of all players
unit_manager.filter_units_by_const(unit_consts=[BuildingInfo.TOWN_CENTER.ID])
# Get TC object of only player one and two
unit_manager.filter_units_by_const(unit_consts=[BuildingInfo.TOWN_CENTER.ID], player_list=[PlayerId.ONE, PlayerId.TWO])
# Get all objects of player one except for the villagers
unit_manager.filter_units_by_const(
    unit_consts=[UnitInfo.VILLAGER_MALE, UnitInfo.VILLAGER_FEMALE],
    blacklist=True,  # <-- When True, everything in the unit_consts list will be excluded instead of included
    player_list=[PlayerId.ONE],
)
# Exclude all unique units from a given list
unit_manager.filter_units_by_const(
    unit_consts=UnitInfo.unique_units(),
    blacklist=True,
    unit_list=[some_list_with_Unit_objects]
)
```

## Editing

While adding units is fun, you might want to change existing units. You
can, for example, change the location of any unit:

```py

from AoE2ScenarioParser.objects.support.tile import Tile

...

unit.tile = Tile(0, 0)  # Will change the units location to the center of tile 0,0
# Equivelant to:
unit.x = 0.5
unit.y = 0.5
```

Besides it's location you can also change the type of unit:

```py
unit.unit_const = UnitInfo.MAN_AT_ARMS.ID    # Units dataset
```

You also might want to change the ownership of a unit. You can do this by 
changing the `player` property in the unit object itself or calling 
`change_ownership` from the unit manager.

```py
# Both are identical in functionality
unit.player = PlayerId.THREE
unit_manager.change_ownership(unit, PlayerId.THREE)
```

## Removing

Two ways to delete a unit:

> [!TIP]
> **Removing a unit using an object is faster**  
> Due to a unit object containing the player value it belongs to, 
> the unit can be found a lot faster. Which, when removing a lot of units,
> can save you some time.


```py
unit_manager.remove_unit(unit=unit)
unit_manager.remove_unit(reference_id=unit.reference_id)
```

If you want to remove all units from the map or a single player 
you can also just set it to an empty list:

```py
# Remove all units from P3
unit_manager.units[PlayerId.THREE] = []
# Remove all units
unit_manager.units = []
```

## Other functions

Ever wanted to get rid of all the eye candy on the map? Now you can:

```py
unit_manager.remove_eye_candy()
```


---

# 地图 Map


# Map

You can use the map manager to adjust the terrain, elevation, map size and other attributes.

## Map Size

You can adjust the map size using the parser. 

> [!WARNING]
> **Only rectangular maps**  
> The game only supports square maps. Changing the size to a rectangle that is not a square will cause the game to crash.


> [!WARNING]
> **Maximum size is 480**  
> The game does not support maps over the size of 480. Beyond this size the game will crash when you test the scenario.


You can adjust the map size like so:

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

# File & Folder setup
# Define paths to the scenario folder.
# You can find this folder by opening AoE2:DE and going to scenarios and clicking on 'open folder'
scenario_folder = "your/path/to/the/scenario/folder/"  # <-- Final slash is important
scenario_name = "name_of_your_scenario"

# Define Scenario file
scenario = AoE2DEScenario.from_file(f"{scenario_folder}{scenario_name}.aoe2scenario")

# Add Trigger
map_manager = scenario.map_manager
# Set it to a nice small 10x10 map :)
map_manager.map_size = 10

# Write to same folder with name + '_output'
scenario.write_to_file(f"{scenario_folder}{scenario_name}_output.aoe2scenario")
```

## Terrain

You can also edit terrain tiles.

### Terrain Tiles

Each terrain tile has 3 properties. It's `elevation`, `terrain_id` and `layer`.
You can request this information using: 

```py
tile = map_manager.get_tile(0, 0)
tile.terrain_id
tile.elevation
tile.layer
```

You can also edit this information, for example if you want to change tile 20 into water, you can:

```py
from AoE2ScenarioParser.datasets.terrains import TerrainId

tile = map_manager.get_tile(i=19)  # (0 based, 0 is the 1st tile, 1 is the second tile etc.)
tile.terrain_id = TerrainId.WATER_SHALLOW
```

You can also request `readonly` properties from a tile, like its index or coordinates.  
These **cannot** be edited.

```py
tile = map_manager.get_tile(0, 0)
tile.i      # 85  (Same tile as when you do: map_manager.terrain[85])
tile.x      # 5
tile.y      # 8
tile.xy     # (5, 8)  <-- Tuple(5,8)
```

### Selection

There's multiple ways to get access to the terrain tiles. The first thing you can do is get access to the entire terrain
list through:

```
map_manager.terrain  # Returns a one dimensional list of TerrainTile objects
```

The list is the map stacked in a single list. The first entry in the list is the most `West` tile in the scenario.
The second entry is the tile to the top right of the last one. The third is on the top right of that one. This continues
until you hit the North East edge. Then it'll continue with the tile to the bottom right of the first tile and the tile
after that is the tile to the top right of it. 

Below you can see a visualisation of a 10x10 map. The coords are `(X,Y)` coordinates and the blue line is the order in 
which tiles are saved.

![Visualisation Map Tiles Explained](../images/map_tiles_explained.png "map_tiles_explained")

To get a tile based on it's XY coordinate (like `(5,8)`, as highlighted in the above image) you can use:

```py
map_manager.get_tile(x=5, y=8)  # Get tile at x5,y8
map_manager.get_tile(i=85)      # Get the 86th tile (0 based, 0 is the 1st tile, 1 is the second tile etc.)
```

You can also get a square of tiles from the map. For this you can use the function `get_square_1d()` or 
`get_square_2d()`. Both the functions will return the same tiles, but one will result in a list of tiles, the other in a 
list of list with tiles.

For example, if you want to turn a square of tiles into roads:

```py
from AoE2ScenarioParser.datasets.terrains import TerrainId

# Using: get_square_1d
for tile in map_manager.get_square_1d(x1=4, y1=4, x2=8, y2=8):
    tile.terrain_id = TerrainId.ROAD

# Using: get_square_2d
for tile_row in map_manager.get_square_2d(x1=4, y1=4, x2=8, y2=8):
    for tile in tile_row:
        tile.terrain_id = TerrainId.ROAD
```

This will turn the above map into:

![Visualisation Map Tiles With Road](../images/map_tiles_with_road.png "map_tiles_with_road")

## Elevation

You can also add hills to the map by using the `set_elevation` function. 
In the below graphic you can see the coordinates used in the function. 

![](../images/map_coordinates_explained.png)
Thanks to [ScribbleGhost](https://github.com/ScribbleGhost) for the graphic! ❤️

```py
map_manager.set_elevation(
    elevation=1,
    x1=3, 
    y1=6, 
    x2=9, 
    y2=12,
)
```

> [!TIP]
> **Elevation is also zero based**  
> Elevation is zero based, 0 represents what Age2 calls elevation 1, 1 represents elevation 2 etc.


This will create a hill of elevation **3** in the game. The top square of the hill will be 3x3 tiles. Because (3,3) to
(5,5) shown in the function above represents the top of the hill. The entire hill, including the slopes, will start on:
(1,1) to (7,7).

> [!WARNING]
> **Don't go too high!**  
> Using the parser you can basically go as high as you want, **BUT** above ~20 without UHD and ~15 with UHD the 
> camera starts clipping into the hill. 



---

# 玩家 Players


# Players

You can use the player manager to edit many player related attributes.

## Editing

Here's an example of how to view a player and edit their starting civilization, architecture and resources.

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.object_support import Civilization
from AoE2ScenarioParser.datasets.players import PlayerId

# File & Folder setup
# Define paths to the scenario folder.
# You can find this folder by opening AoE2:DE and going to scenarios and clicking on 'open folder'
scenario_folder = "your/path/to/the/scenario/folder/"  # <-- Final slash is important
scenario_name = "name_of_your_scenario"

# Define Scenario file
scenario = AoE2DEScenario.from_file(f"{scenario_folder}{scenario_name}.aoe2scenario")

# Save the player manager and the second player
player_manager = scenario.player_manager
player_two = player_manager.players[PlayerId.TWO]

player_two.civilization = Civilization.BYZANTINES
player_two.architecture_set = Civilization.BYZANTINES
player_two.food = 550
player_two.wood = 450
player_two.gold = 350
player_two.stone = 250

# Write to same folder with name + '_output'
scenario.write_to_file(f"{scenario_folder}{scenario_name}_output.aoe2scenario")
```

Players have many attributes, below is a list of most of their attributes which you can change.

| Attribute name        | Type      | Dataset      | Attributes |
|-----------------------|-----------|--------------|------------|
| player_id             | int       | -            | Read only  |
| active                | bool      | -            | Read onl   |
| starting_age          | int       | StartingAge  |            |
| lock_civ              | bool      | -            |            |
| population_cap        | int       | -            |            |
| food                  | int       | -            |            |
| wood                  | int       | -            |            |
| gold                  | int       | -            |            |
| stone                 | int       | -            |            |
| color                 | int       | ColorId      |            |
| human                 | bool      | -            |            |
| civilization          | int       | Civilization |            |
| architecture_set      | int       | Civilization |            |
| diplomacy             | List[int] | -            | Non-GAIA   |
| ~~initial_camera_x~~* | int       | -            | Non-GAIA   |
| ~~initial_camera_y~~* | int       | -            | Non-GAIA   |
| allied_victory        | bool      | -            | Non-GAIA   |
| disabled_techs        | List[int] | -            | Non-GAIA   |
| disabled_buildings    | List[int] | -            | Non-GAIA   |
| disabled_units        | List[int] | -            | Non-GAIA   |
| tribe_name            | str       | -            | Non-GAIA   |
| base_priority         | int       | -            | Non-GAIA   |
| string_table_name_id  | int       | -            | Non-GAIA   |
| initial_player_view_x | int       | -            | Non-GAIA   |
| initial_player_view_y | int       | -            | Non-GAIA   |

*: Deprecated properties which don't affect anything

## Active Players

You can also set the active players with the player manager. Unfortunately, the game does not
support enabling players in 'gaps'. If you want p4 enabled, you need to have p1, p2 and p3 enabled.
This is why the 'active' attribute in the player object is read-only.

You can set the active player like:

```py
player_manager.active_players = 4  # Enables player 1, 2, 3 and 4
```

## Disables

Disables are used to disable units, buildings and technologies for a certain player.
For example, if you want to disable `archery ranges`, `stables` and `siege workshops` for player two,
and you want to disable the `market`, the tech `loom` and `Paladins` for the fifth player, you can do so like this:

```py
player_two = player_manager.players[PlayerId.TWO]
player_two.disabled_buildings.extend([
    BuildingInfo.ARCHERY_RANGE.ID,
    BuildingInfo.STABLE.ID, 
    BuildingInfo.SIEGE_WORKSHOP.ID
])

player_five = player_manager.players[PlayerId.FIVE]
player_five.disabled_buildings.append(BuildingInfo.MARKET.ID)
player_five.disabled_techs.append(TechInfo.LOOM.ID)
player_five.disabled_units.append(UnitInfo.PALADIN.ID)
```

You can also copy the list of units from one player to another:

```py
player_two = player_manager.players[PlayerId.TWO]
player_five = player_manager.players[PlayerId.FIVE]

player_five.disabled_buildings = player_two.disabled_buildings.copy()
```

## Diplomacy

You can set diplomacy through the player manager or directly per player.

### Set diplomacy teams

If you want to quickly set the diplomacy in teams where everyone is allied to the rest of the team, you can use the `player_manager.set_diplomacy_teams` function.
It accepts a list of lists with integers or `PlayerId` numbers.

The code below creates four teams of two. This sets the players to ally as you can see with the final `diplomacy` argument.

```py
player_manager.set_diplomacy_teams(
    [1, 2], [3, 4], [5, 6], [7, 8], 
    diplomacy=DiplomacyState.ALLY
)
```

### Set diplomacy directly

You can also set the diplomacy directly for a single player. 
For example, below you can see that player one is set to enemy with player 5 and player 2, 3 and 4 are set to ally.

> [!NOTE]
> **This is not mutual!**  
> These function calls will only set the diplomacy one-way.  
> All 'target' players (2, 3, 4 and 5) are still on the default Enemy stance.


```py
p1 = player_manager.players[PlayerId.ONE]
p1.set_player_diplomacy(5, DiplomacyState.ENEMY)
p1.set_player_diplomacy([2, 3, 4], DiplomacyState.ALLY)
```


---

# 区域 Area


# Area

The ``Area`` object is a powerful object to get access to specific regions on the map. 
This page will try to explain a bit on how to use it and what the possibilities are.

First of all, the `Area` object uses "Method Chaining". 
This means that methods inside the `Area` object return the `Area` object itself.
This allows you to call another method straight after the first: 

```py
obj.x()
obj.y()
obj.z()
# With method chaining you can do:
obj.x().y().z()
```

This is perfect for a highly configurable and flexible objects like the `Area` object.

---

## Why would I use the `Area` object?

If you want to do anything with more than a single coordinate, it's quite the hassle sometimes.
That's the problem this object is _trying_ (feature suggestions always welcome!) to solve.

> [!NOTE]
> The `Area` object strength comes from selecting specific pattern/tiles. If you want to do a similar thing with 
> every tile on the map this object won't help you much. 


---

## Area functions

To view every function that exists on an Area object, view the <a href="api/AoE2ScenarioParser/objects/support/area.html#Area" target="_blank" class="btn btn-primary">Area API Reference</a>.

## Examples

Below are a couple examples that show why this object can be very useful when working with coordinates.

### Creating a stack of units

Let's say you want to place 16 units, in a 4x4 area on the map. 
This is not necessarily difficult to do, it'd probably look something like the following:

```py
for x in range(10, 14):
    for y in range(50, 54):
        unit_manager.add_unit(
            player=PlayerId.ONE, 
            unit_const=UnitInfo.KNIGHT.ID, 
            x=x+.5, 
            y=y+.5
        )
```

This would create 16 units in a 4x4 area and isn't too bad to read or write.
Though, having an object which manages the area would be a lot cleaner than looping through coordinates.
So, let's see how we'd do it with the `Area` object.

```py
area = scenario.new.area()  # Create a new area object

# Select the area and convert it to a set of all coordinates inside of it
for tile in area.select(10, 50, 13, 53).to_coords():
    # Every tile is a NamedTuple with an 'x' and 'y' value
    unit_manager.add_unit(
        player=PlayerId.ONE, 
        unit_const=UnitInfo.KNIGHT.ID, 
        x=tile.x + .5, 
        y=tile.y + .5
    )
```

Above we can see the creation of a new `Area` object through the new Object Factory inside a scenario.
We use the `select` method to select our area. 

> [!NOTE]
> Keep in mind that `Area.select` uses an inclusive selection. 
> This means that doing: `area.select(1, 1, 3, 3)` will select a 3x3 area.


---

### Castle surrounded by walls

Now, the above example was quite a simple one. The real power comes with the configuration!
So let's take a more complicated example! Like creating a wall around a castle!
This will be quite the difference, so let's do it in steps, first we create the castle and the area object.

```py
castle = unit_manager.add_unit(player=PlayerId.ONE, unit_const=BuildingInfo.CASTLE.ID, x=30, y=30)
area = scenario.new.area()
```

Now let's select the area of the castle itself, so the 4x4 area.

```py
area.center(castle.x, castle.y).size(4)
# Or using separate width and height calls:
area.center(castle.x, castle.y).width(4).height(4)
```

This sets the center of the area to the castles coordinates. 
After that we change the size of the selection from the default (1x1) to (4x4).
We now have the castle area selected. Let's say we want the wall 6 tiles around the castle.
Let's expand our selection by 6 tiles.

```py
# On it's own line
area.expand(6)
# Or add it to the above line
area.center(castle_object.x, castle_object.y).size(4).expand(6)
```

Now we have a 16 by 16 tile area selected.
The 4x4 from the castle plus the 6 tiles we expanded to all four sides.

We _could_ do the same thing as above with the knights in the 4x4 but there's a problem.
The selection covers all those 256 (16*16) tiles. So we'd be filling everything with walls. 
We just want the edges so, let's do that. For that we use a so called "use" function.

```py
# On it's own line
area.use_only_edge()
# Or, again, add it to the above line
area.center(castle_object.x, castle_object.y).size(4).expand(6).use_only_edge()
```

This tells the area object we only want the outer edge of the selection.
Now let's convert that to coordinates and place those walls! We can use `area.to_coords()` again!

```py
castle = unit_manager.add_unit(player=PlayerId.ONE, unit_const=BuildingInfo.CASTLE.ID, x=30, y=30)
area = scenario.new.area()

for tile in area.center(castle.x, castle.y).size(4).expand(6).use_only_edge().to_coords():
    unit_manager.add_unit(
        player=PlayerId.ONE, unit_const=BuildingInfo.STONE_WALL.ID, x=tile.x, y=tile.y
    )
```

And that's it! The castle has walls around it. With such ease!

![Caslte With Walls](../images/area_castle_walls.png "area with castle walls")

---

### Checkers pattern

So, let's say we want to create a checkers pattern. 
Where we create squares of ice and black terrain alternately.
To do this we basically need all tiles on the map but in separate squares.
So selecting the entire map alone isn't enough here as we want them all separated.

So, what we want is blocks of 3x3 over the course of the map. 
The map we're reading is a tiny 2 player map which has a size of 120 by 120 tiles.

What we'll do is select the entire map and use the grid pattern. 
Then we use a block size of 3 and a gap size of 0. This way we get 3x3 areas.

Though, we cannot use the `area.to_coords()` function we used before. 
The reason for that is because the function returns all tiles in the selection. 
And because we use all tiles in the map, this function will just return a large list of all tiles.
What we need for this is: `area.to_chunks()`. Let's get started and see how it works!

Alright, first, let's create the main `Area` object and select the entire map. 

```py
area = scenario.new.area()
area.select_entire_map()
```

After that, let's set it so that it uses the grid pattern. You can do this in two ways:

```py
# Append to the same line
area = scenario.new.area()
area.select_entire_map().use_pattern_grid()

# Or add it after the last line
area = scenario.new.area()
area.select_entire_map()
area.use_pattern_grid()
```

Now this would be default return a grid with gaps of 1 and blocks of 1x1. We want blocks of 3x3 and no gaps (gap of 0).
Below you can see the steps and the difference these configurations have:

![Area grid 1x1 example](../images/area_grid_1x1_example.png "Area grid 1x1 example")

Now that we know what we want, we can add some configuration to the function, we can do this in four ways, choose 
the one you like the most (We'll continue with the first option):

```py
# For the third option:
from AoE2ScenarioParser.objects.support.area import AreaAttr

...
area.use_pattern_grid(block_size=3, gap_size=0)
...
area.use_pattern_grid().attr('block_size', 3)
area.use_pattern_grid().attr('gap_size', 0)
...
area.use_pattern_grid().attr(AreaAttr.BLOCK_SIZE, 3)
area.use_pattern_grid().attr(AreaAttr.GAP_SIZE, 0)
...
area.use_pattern_grid().attrs(block_size=3, gap_size=0)
```

> [!TIP]
> **You can differentiate the X and Y**  
> In many functions you can use the general option like `gap_size`. 
> But there's also options for `gap_size_x` and `gap_size_y` if you want different selections.


Now that we have the grid, let's add the final piece where we change the terrain itself. 
We can use the function `to_chunks()` to return our grid as 'chunks'.

Chunks will be returned in a list and every chunk will be returned as an `OrderedSet`.
These `OrderedSet`s will contain `Tile` objects by default. These objects just contain their `x` and `y` values.
We can change this behaviour with the `as_terrain` parameter. 
Setting this to `True` will return the `OrderedSet`s with `TerrainTile` objects. 
These objects allow you to directly change the terrain on this tile. 
These are also the same objects returned by the Map Manager.

```py
for index, chunk in enumerate(area.to_chunks(as_terrain=True)):
    for terrain_tile in chunk:
        terrain_tile.terrain_id = TerrainId.BLACK if index % 2 == 0 else TerrainId.ICE
```

So the code above loops through all the 3x3 squares returned by the `to_chunks` function.
Then for each square it loops through all the terrain tiles in the `OrderedSet`.
We then set the terrain to `BLACK` or `ICE` depending on the index reduced by modulo 2.
This will alternate the tiles between the two terrain types.

There's one small adjustment we need to make. Because the map 120 tiles and the squares have a length of 3 we can fit
40 squares per row. This is an even number. So just alternating `BLACK` and `ICE` terrain based on index will cause
it to create lines instead of alternating each row. We can fix this by adding the row with the index and reduce that
by modulo 2 to get our ideal situation. 

```py
for index, chunk in enumerate(area.to_chunks(as_terrain=True)):
    for terrain_tile in chunk:
        row = index // (map_manager.map_size / 3)  # 3 as the size of the grid blocks
        terrain_tile.terrain_id = TerrainId.BLACK if (index + row) % 2 == 0 else TerrainId.ICE
```

Another way to get around this is make sure the squares fit an odd amount of times in the length of the map. 
So using the earlier loop, without the row, with a map size of 117 (39 times) would result in the same pattern as the 
code above.

![area checkers example result](../images/area_checkers_example_result.png "area checkers example result")

The entire code block for this example:

```py
area = scenario.new.area()
area.select_entire_map().use_pattern_grid(block_size=3, gap_size=0)

for index, chunk in enumerate(area.to_chunks(as_terrain=True)):
    for terrain_tile in chunk:
        row = index // (map_manager.map_size / 3)  # 3 as the size of the grid blocks
        terrain_tile.terrain_id = TerrainId.BLACK if (index + row) % 2 == 0 else TerrainId.ICE
```

---

The API Documentation has existed for some time, and the temporary docs here, have been removed.

They've been moved here: <a href="/api/AoE2ScenarioParser/objects/support/area.html#Area" target="_blank" class="btn btn-primary">Area API Reference</a>.


---

# 数据集 Datasets


# Datasets

The project currently contains multiple datasets. You can get access to the datasets by importing them.

```py
# Information about the conditions & effects and their attributes
from AoE2ScenarioParser.datasets.conditions import ConditionId
from AoE2ScenarioParser.datasets.effects import EffectId
from AoE2ScenarioParser.datasets.object_support import Civilization, StartingAge
from AoE2ScenarioParser.datasets.trigger_lists import VisibilityState, VictoryTimerType, UnitTrait, UnitAIAction, \
    TimeUnit, TerrainRestrictions, TechnologyState, SelectionEffect, SecondaryGameMode, ProjectileVanishMode, \
    ProjectileSmartMode, ProjectileHitMode, PanelLocation, OcclusionMode, ObstructionType, ObjectType, ObjectState, \
    ObjectClass, ObjectAttribute, Hotkey, HeroStatusFlag, GarrisonType, FogVisibility, DiplomacyState, DifficultyLevel, \
    DamageClass, Comparison, CombatAbility, ColorMood, ChargeType, ChargeEvent, ButtonLocation, BlockageClass, \
    BlastLevel, AttackStance, ActionType, Attribute, Operation

# Information of unit/building/hero and tech IDs
from AoE2ScenarioParser.datasets.projectiles import ProjectileInfo
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.heroes import HeroInfo
from AoE2ScenarioParser.datasets.other import OtherInfo
from AoE2ScenarioParser.datasets.techs import TechInfo
from AoE2ScenarioParser.datasets.units import UnitInfo

# Information about terrain IDs
from AoE2ScenarioParser.datasets.terrains import TerrainId

# Information about player IDs
from AoE2ScenarioParser.datasets.players import PlayerId, PlayerColorId, ColorId
```

A special thanks to **Alian713** for doing **A LOT** of the work in contributing the data needed for these datasets. :heart:

---

## Conditions & Effects

The condition and effect datasets aren't really necessary in regular scripting after adding the new methods for adding
effects & conditions:

```py
effect = trigger.new_effect.change_diplomacy(...)
```

They can still be used if you want the effect & condition IDs for other purposes.

```py
ConditionId.OBJECTS_IN_AREA  # 5
EffectId.PATROL  # 19
```

```py
# Checking the docs for EffectId.CHANGE_DIPLOMACY will show:
"""
Attributes for the **change_diplomacy** effect are:
- diplomacy
- player_source
- player_target
"""
```

---

## Conditions & Effects lists

Many conditions and effects have dropdown lists with options. These options are, like everything else, impossible to
remember. That's why these datasets have been added:

<a href="api/index.html" target="_blank">Also view the API docs for these datasets</a> (bottom of the list)

| Names                      | Explanation                                                                         | Example                                      |
|----------------------------|-------------------------------------------------------------------------------------|----------------------------------------------|
| ActionType                 | Used in the `Task Object` effect.                                                   | `ActionType.ATTACK_GROUND`                   |
| Age                        | Used in the `Modify Resource` effect. With the `Current Age` resource.              | `Age.CASTLE_AGE`                             |
| AttackStance               | Used in the `Change Object Stance` effect.                                          | `AttackStance.AGGRESSIVE_STANCE`             |
| Attribute                  | Used in the `Accumulate Attribute` effect.                                          | `Attribute.ALL_TECHS_ACHIEVED`               |
| BlastLevel                 | Can be used for changing the `BLAST_<>_LEVEL` properties in `ObjectAttribute`.      | `BlastLevel.NEARBY_UNITS`                    |
| BlockageClass              | Used in the `Modify Attribute` effect. With the `Blockage Class` attribute.         | `BlockageClass.RESOURCE`                     |
| ButtonLocation *           | Used in the `Change Research Location` and `Change Train Location` effects. *       | `ButtonLocation.r2c3`                        |
| ChargeEvent                | Used in the `Modify Attribute` effect. With the `Charge Event` attribute.           | `ChargeEvent.NO_CHARGE_DEPLETED`             |
| ChargeType                 | Used in the `Modify Attribute` effect. With the `Charge Type` attribute.            | `ChargeType.AREA_ATTACK_CHARGE`              |
| ColorMood                  | Used in the `Change Color Mood` effect.                                             | `ColorMood.WINTER`                           |
| CombatAbility              | Used in the `Modify Attribute` effect. With the `Combat Ability` attribute.         | `CombatAbility.ATTACK_GROUND`                |
| Comparison                 | Used in many effects and conditions. Generally related to variables.                | `Comparison.EQUAL`                           |
| DamageClass                | Used in the `Change Object Attack/Armour` effects.                                  | `DamageClass.SPEARMEN`                       |
| DifficultyLevel            | Used in the `Difficulty Level` condition.                                           | `DifficultyLevel.HARDEST`                    |
| DiplomacyState             | Used in the `Change Diplomacy` effect and the `Diplomacy State` condition.          | `DiplomacyState.ALLY`                        |
| FogVisibility              | Used in the `Modify Attribute` effect. With the `Fog Visibility` attribute.         | `FogVisibility.ALWAYS_VISIBLE`               |
| GarrisonType               | Used in the `Modify Attribute` effect. With the `Garrison Type` attribute.          | `GarrisonType.CAVALRY`                       |
| HeroStatusFlag *           | Can be used for changing the `HERO_STATUS` in `ObjectAttribute`. *                  | `HeroStatusFlag.HERO_REGENERATION`           |
| Hotkey                     | Can be used for changing the `HOTKEY_ID` in `ObjectAttribute`.                      | `Hotkey.SPACE`                               |
| ObjectAttribute            | Used in the `Modify Attribute` effect.                                              | `ObjectAttribute.CARRY_CAPACITY`             |
| ObjectClass                | Used in every unit selection effect & condition.                                    | `ObjectClass.INFANTRY`                       |
| ObjectState                | Used in the `Objects in area` condition.                                            | `ObjectState.DEAD`                           |
| ObjectType                 | Used in every unit selection effect & condition.                                    | `ObjectType.DOPPELGANGER`                    |
| ObstructionType            | Used in the `Modify Attribute` effect. With the `Obstruction Type` attribute.       | `ObstructionType.SQUARE_OUTLINE_COLLISION`   |
| OcclusionMode              | Used in the `Modify Attribute` effect. With the `Occlusion Mode` attribute.         | `OcclusionMode.DISPLAY_OUTLINE`              |
| Operation                  | Used in many effects. Generally related to variables.                               | `Operation.MULTIPLY`                         |
| PanelLocation              | Used in the `Display Instructions` effect.                                          | `PanelLocation.CENTER`                       |
| ProjectileHitMode          | Used in the `Modify Attribute` effect. With the `Projectile Hit Mode` attribute.    | `ProjectileHitMode.ANY_PLAYER_UNIT`          |
| ProjectileSmartMode        | Can be used for changing the `ENABLE_SMART_PROJECTILES` in `ObjectAttribute`.       | `ProjectileSmartMode.TARGET_FUTURE_LOCATION` |
| ProjectileVanishMode       | Used in the `Modify Attribute` effect. With the `Projectile Vanish Mode` attribute. | `ProjectileVanishMode.PASS_THROUGH`          |
| SecondaryGameMode          | Used for setting the secondary victory conditions.                                  | `SecondaryGameMode.SUDDEN_DEATH`             |
| SelectionEffect            | Used in the `Modify Attribute` effect. With the `Selection Effect` attribute.       | `SelectionEffect.HP_BAR_OUTLINE`             |
| StartingAge                | Used in the player manager for setting the player starting age.                     | `StartingAge.FEUDAL_AGE`                     |
| TechnologyState            | Used in the `Technology State` condition.                                           | `TechnologyState.RESEARCHING`                |
| TerrainRestrictions        | Can be used for changing the `TERRAIN_RESTRICTION_ID` in `ObjectAttribute`.         | `TerrainRestrictions.LAND`                   |
| TimeUnit                   | Used in the `Display Timer` effect.                                                 | `TimeUnit.YEARS`                             |
| UnitAIAction               | Used in the `Object has Action` condition.                                          | `UnitAIAction.ATTACK`                        |
| UnitTrait                  | Used in the `Modify Attribute` effect. With the `Unit Trait` attribute.             | `UnitTrait.SHIP`                             |
| VictoryTimerType           | Used in the `Victory Timer` condition.                                              | `VictoryTimerType.KING_OF_THE_HILL_TIMER`    |
| VisibilityState            | Used in the `Set Player Visibility` effect.                                         | `VisibilityState.EXPLORED`                   |
| ObjectModifyAttributeState | Used in the `Modify Object Attribute` effect.                                       | `ObjectModifyAttributeState.NOT_MODIFIED`    |

\*: Means extra functionality listed below.

### ButtonLocation

```py
ButtonLocation.row_col(1, 3)  # ButtonLocation.r1c3
```

### HeroStatusFlag

```py
# Both have the same result
hsf = HeroStatusFlag.CANNOT_BE_CONVERTED + HeroStatusFlag.DELETE_CONFIRMATION
hsf = HeroStatusFlag.combine(
    cannot_be_converted=True,
    delete_confirmation=True
)
```

---

### General usage examples:

```py
trigger = trigger_manager.add_trigger("Inform Betrayal!")
condition = trigger.new_condition.diplomacy_state(
    quantity=DiplomacyState.ALLY,  # <-- DiplomacyState dataset
    source_player=PlayerId.TWO,
    target_player=PlayerId.THREE
)

effect = trigger.new_effect.display_instructions(
    source_player=PlayerId.ONE,
    message="Spy: Your ally has betrayed you! He allied the enemy!",
    instruction_panel_position=PanelLocation.CENTER,  # <-- PanelLocation dataset
    display_time=10
)
```

---

## Unit, Building, Techs etc.

The Units and Buildings datasets are very useful when adding units.  
They're also, together with the `Tech` dataset, very useful when adding or editing triggers.

### General Usage

These are the biggest and most powerful datasets:

| Dataset        | Description                                          |
|----------------|------------------------------------------------------|
| `UnitInfo`     | Dataset for units                                    |
| `BuildingInfo` | Dataset for buildings                                |
| `HeroInfo`     | Dataset for heroes                                   |
| `OtherInfo`    | Dataset for other units (like relics and gold piles) |
| `TechInfo`     | Dataset for technologies                             |

> [!TIP]
> **The use of the `.ID` suffix**  
> These datasets contain more info about the object than just the ID.  
> To be able to access all this info from a single entry, suffix are needed to specifically request the right 
> information.  
> If you want the normal ID of a unit/building etc. you need to use: `.ID` after the dataset entry.  
> This will look something like: `UnitInfo.PALADIN.ID`

    

For adding units it'll look something like the following:

```py
unit_manager.add_unit(PlayerId.ONE,  UnitInfo.CONQUISTADOR.ID,    x=10, y=20)
unit_manager.add_unit(PlayerId.TWO,  UnitInfo.PALADIN.ID,         x=20, y=20)
unit_manager.add_unit(PlayerId.GAIA, BuildingInfo.FEITORIA.ID,    x=30, y=20)
unit_manager.add_unit(PlayerId.GAIA, HeroInfo.WILLIAM_WALLACE.ID, x=40, y=20)
unit_manager.add_unit(PlayerId.GAIA, OtherInfo.GOLD_MINE.ID,      x=50, y=20)
```

With the triggers you can do similar stuff like:

```py
...
effect = trigger.new_effect.create_object(
    object_list_unit_id=OtherInfo.RELIC.ID
)
...
effect = trigger.new_effect.research_technology(
    source_player=PlayerId.THREE,
    technology=TechInfo.BLOODLINES.ID
)
...
```

### UnitInfo functions

Some useful functions for the `UnitInfo` dataset is `vils()` and `unique_units()`

```py
# Get all villager units (e.g. FARMER, HUNTER, LUMBERJACK etc.) 
# You can disable certain categories like:
# - exclude_male
# - exclude_female
# Example:
male_vils = UnitInfo.vils(exclude_female=True)  
```

```py
# Get all unique units (e.g. HUSKARL, CONQUISTADOR, LONGBOAT, SLINGER etc.)
# You can disable certain categories like:
# - exclude_elite_units
# - exclude_non_elite_units
# - exclude_castle_units  (From the castle building)
# - exclude_non_castle_units  (From anything but the castle building)
# Example:
all_unique_non_castle_non_elite_units = UnitInfo.unique_units(exclude_elite_units=True, exclude_castle_units=True)  
```

### TechInfo functions

Some useful functions for the `TechInfo` dataset are:

- `unique_techs()`

```py
# Get all unique techs (e.g. BEARDED_AXE, CHIEFTAINS, FIRST_CRUSADE etc.)
# You can disable certain categories like:
# - exclude_castle_techs
# - exclude_imp_techs
# Example:
imp_unique_techs = TechInfo.unique_techs(exclude_castle_techs=True)  
```

- `unique_unit_upgrades()`

```py
# Get all unique unit techs (e.g. ELITE_LONGBOWMAN, ELITE_TEUTONIC_KNIGHT etc.)
# You can disable certain categories like:
# - exclude_castle_techs
# - exclude_non_castle_techs  (Excludes stuff like: ELITE_LONGBOAT, IMPERIAL_SKIRMISHER)
# Example:
uu_castle_upgrades = TechInfo.unique_unit_upgrades(exclude_non_castle_techs=True)  
```

- `blacksmith_techs()`
- `monastery_techs()`
- `university_techs()`
- `town_center_techs()`

```py
# Get all blacksmith/monastery/university techs
# You can filter on ages, like so:
all_blacksmith_techs = TechInfo.blacksmith_techs()
feudal_blacksmith_techs = TechInfo.blacksmith_techs(Age.FEUDAL_AGE)
non_imp_blacksmith_techs = TechInfo.blacksmith_techs([Age.FEUDAL_AGE, Age.CASTLE_AGE])
# Same goes for:
#   - TechInfo.monastery_techs(...)
#   - TechInfo.university_techs(...)
#   - TechInfo.town_center_techs(...)
```

- `eco_techs()`

```py
# Get all economic techs
all_eco_techs = TechInfo.eco_techs()
# You can filter on ages (like with blacksmith_techs etc.):
dark_age_eco_techs = TechInfo.eco_techs(ages=Age.DARK_AGE)  # Only returns LOOM
# Or filter on buildings
mining_and_lumber_upgrades = TechInfo.eco_techs(
    buildings=[BuildingInfo.MINING_CAMP.ID, BuildingInfo.LUMBER_CAMP.ID]
)
# Or both:
imp_tc_upgrades = TechInfo.eco_techs(
    ages=Age.IMPERIAL_AGE,
    buildings=BuildingInfo.TOWN_CENTER.ID,
)
```

### OtherInfo functions

One useful function for the `OtherInfo` dataset is `trees()`:

```py
# Get all tree objects (e.g. OAK_TREE, PINE_TREE, BAMBOO etc.)
# Example:
all_trees = OtherInfo.trees()  
```

### Icon, Dead & Hotkey IDs

Besides normal IDs, you might want to access their icon or dead version. Almost every unit, building, hero and tech has
an icon. Most units, buildings and heroes also have a dead unit version to represent the dying animation.  
You can access these values using the same datasets:

```py
archer_id =        UnitInfo.ARCHER.ID         # 4
archer_icon =      UnitInfo.ARCHER.ICON_ID    # 17
archer_death =     UnitInfo.ARCHER.DEAD_ID    # 3
archer_hotkey_id = UnitInfo.ARCHER.HOTKEY_ID  # 16083

# You can also get the datasets from these values
UnitInfo.from_id(4)             # UnitInfo.ARCHER
UnitInfo.from_icon_id(17)       # UnitInfo.ARCHER
UnitInfo.from_dead_id(3)        # UnitInfo.ARCHER
UnitInfo.from_hotkey_id(16083)  # UnitInfo.ARCHER

# It's also still possible to use the string like normal enums:
UnitInfo["ARCHER"]  # UnitInfo.ARCHER
```

---

### GAIA

If you want to know if a unit etc. is a gaia only object, you can do:

```py
UnitInfo.ARCHER.IS_GAIA_ONLY  # False
UnitInfo.WOLF.IS_GAIA_ONLY  # True

# Or for a list:
UnitInfo.gaia_only()  # Returns all units which have 'IS_GAIA_ONLY' as True
UnitInfo.non_gaia()  # Returns all units which have 'IS_GAIA_ONLY' as False
```

---

## Projectiles

If you wanted to change a projectile of archers to that of an arambai, you could do:

```py
trigger.new_effect.modify_attribute(
    quantity=ProjectileInfo.ARAMBAI.ID,
    object_list_unit_id=UnitInfo.ARCHER.ID,
    source_player=PlayerId.ONE,
    operation=Operation.SET,
    object_attributes=ObjectAttribute.PROJECTILE_UNIT
)
```

Not all projectiles have the most obvious names. So you can use the following to find projectiles easier.

```py
# Get the second projectile that a CHU KO NU shoots. (Pre-chemistry arrows)
ProjectileInfo.get_unit_projectile(UnitInfo.CHU_KO_NU.ID, has_chemistry=False, secondary=True)
```

---

## Terrains

The terrain dataset can be used for changing terrain types.

```py
TerrainId.BEACH  # 2
TerrainId.FOREST_OAK  # 10
TerrainId.UNDERBUSH_LEAVES  # 71

# Changing the terrain could be done like so:
map_manager.terrain[0].terrain_id = TerrainId.GRASS_1
```

---

## Players

For selecting players it can be as easy as typing `1`. Unfortunately not all parts of the scenario file are structured
like: `0: Gaia, 1: Player1 ... 8: Player8`. So because of this a representation layer has been added. It's a simple Enum
which looks like this:

```py
PlayerId.GAIA,
PlayerId.ONE, PlayerId.TWO, PlayerId.THREE, PlayerId.FOUR,
PlayerId.FIVE, PlayerId.SIX, PlayerId.SEVEN, PlayerId.EIGHT
```

If you want to loop through players, you have 2 options:

```py
# Python built-in range function:
for player in range(9):  # Or range(1, 9) if you want to exclude GAIA
# ... code...

# The PlayerId function:
for player in PlayerId.all():  # Or PlayerId.all(exclude_gaia=True) if you want to exclude GAIA
# ... code...    
```

You can also address the players by color if you prefer it:

```py
PlayerColorId.BLUE, PlayerColorId.RED, PlayerColorId.GREEN, PlayerColorId.YELLOW,
PlayerColorId.AQUA, PlayerColorId.PURPLE, PlayerColorId.GRAY, PlayerColorId.ORANGE
```

---


---

# XS


# XS Script

For an introduction to the XS scripting language itself, you can check out the [UGC Guide](https://divy1211.github.io/AoE2DE_UGC_Guide/general/xs/beginner/).

## XS-Check

For more information on the XS-Check utility, see the <a href="api/AoE2ScenarioParser/objects/support/xs_check.html" target="_blank">XS-Check API Docs</a> or 
the [XS Check Cheatsheet](xs_check.md).

## Support

Since the introduction of the XS manager, there have been some improvements to the game supporting XS in multiplayer.
Age of Empires 2 Definitive Edition is able to transfer manually referenced XS files (through the XS file field) to
other **players** within your lobby.
Unfortunately this support does not stretch to spectators. They will not be able to watch your games.

To get around this, you can add your XS script to a `Script Call` effect. When you add the XS to such an effect, it 
will, when loading the scenario, move all scripts from those calls to the `default0.xs` file. This does work in 
multiplayer because it happens on every machine separately.

So the XS support for the parser works with a dedicated trigger and a `Script Call` effect. In the in-game editor the 
amount of text in a `Script Call` effect is limited to a certain number of characters. This limitation can be bypassed
using the parser.

## Initialising XS Trigger

You can use the XS manager to add XS to your scenarios. All these XS calls do indeed transfer in multiplayer lobbies
as is explained above. You can use the XS manager like so:

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

# File & Folder setup
scenario_folder = "your/path/to/the/scenario/folder/"
read_file = scenario_folder + "scenario_name.aoe2scenario"

# Define Scenario file
scenario = AoE2DEScenario.from_file(read_file)

xs_manager = scenario.xs_manager
```

Because the `XS Manager` uses a trigger with a `Script Call` in the background, it needs to place the trigger somewhere.
You can call the function below to create the trigger. You can also give it an index to insert it somewhere in the 
scenario. Not adding an index to the call just adds the trigger at the end of the list.

> [!WARNING]
> Placing the trigger at the top of all triggers (`insert_index=0`) can take quite a lot of time if the map already 
> has a lot of triggers (For example over 1000 triggers).


```py
xs_manager.initialise_xs_trigger()
# Or place the XS trigger at the top of all triggers
xs_manager.initialise_xs_trigger(insert_index=0)
```

> [!TIP]
> **You don't have to initialise the trigger**  
> Whenever you call the `add_script()` function (more about this below), 
> it will automatically initialise the trigger if it hasn't been already.
> The use of the `initialise_xs_trigger()` function is **purely** to control where the trigger is placed.


## Adding XS

You can add scripts to the trigger using the `add_script` function. This function accepts a path to an XS file and a 
direct XS script string.

```py
# Add a file to the script. 
# Work on your XS script in a file and this will add it to the scenario
xs_manager.add_script(xs_file_path="path/to/xs/script.xs")

# Add XS directly
xs_script = """
int a = 1;
int b = a + 4;
"""
xs_manager.add_script(xs_string=xs_script)
```
You can use both `xs_file_path=...` and `xs_string=...` in the same `add_script` call too.


---

# XS Check


# XS-CHECK

Support for XS has been greatly improved by the library: [XS-Check](https://github.com/Divy1211/xs-check) made by Alian.

When calling `scenario.write_to_file(...)` all XS that is present in the scenario is combined and sent to the XS-Check 
library. After XS-Check has completed its validation steps the output is analyzed and shown back in the console.

By default, the writing process of AoE2ScenarioParser is **not** interrupted, even if an error is found in the XS code.


> [!WARNING]
> **Only XS from Effects and Conditions is combined**  
> Due to the import logic of XS scripts from many different locations depending on the installation
> location of AoE2:DE, the XS script file that is referenced by filename in the `XsManager` is NOT
> added to the XS-Check library! Scripts added through `xs_manager.add_script(...)` and all other 
> xs from effects and conditions is combined.


## Configurations

There are some configuration options for XS Check in AoE2ScenarioParser. Below you can find the most useful ones.
For more configuration options and more info, see the <a href="api/AoE2ScenarioParser/objects/support/xs_check.html" target="_blank">XS-Check API docs</a>.

### Enabling / Disabling

Disabling XS Check is very simple, you can do so using: 

```py
scenario.xs_manager.xs_check.enabled = False
```

### Raise on error

If you want an exception to be raised when errors are found in your XS file, you can change the following setting:

```py
scenario.xs_manager.xs_check.raise_on_error = True
```

### Timeout

The default timeout for XS Check is 60 seconds. This should be WAY more than most will ever need, but just in case
your XS Check call takes longer than that. You can adjust it using:

```py
scenario.xs_manager.xs_check.timeout_seconds = 120
```

### Using an alternative binary

If you want to use different binaries than the ones that are shipped with AoE2ScenarioParser, you can set the path
to a different binary on your system. You can do so by using:

```py
scenario.xs_manager.xs_check.path = "your/path/to/a/binary"
```

If the binary is of a version that is not technically supported by AoE2ScenarioParser it'll show an error. If you
want to try the unsupported binary anyway, you can also add the following:

```py
scenario.xs_manager.xs_check.allow_unsupported_versions = True
```

## Example

Below is an example of a trigger with a Script Call Effect with some invalid XS with the output that will be printed.

```py
scenario = AoE2DEScenario.from_file(...)
trigger_manager = scenario.trigger_manager

trigger = trigger_manager.add_trigger('My Trigger With XS')

trigger.new_effect.script_call(
    message='void func () {'
            '    int a = 3;'
            '    int b = 4;'
            '    return "";'
            '}'
)

scenario.write_to_file(...)
```

```
-------------------------<[ XS-CHECK VALIDATION RESULT ]>-------------------------

xs-check:0.2.1 output: [ Provided by: https://github.com/Divy1211/xs-check/ ]

	[06] Error: SyntaxError
	   ╭─[AoE2ScenarioParser.xs:1:56]
	   │
	 1 │ /*T0E0*/ void func () {    int a = 3;    int b = 4;    return "";}
	   │                                                        ─────┬────  
	   │                                                             ╰────── This function's return type was declared as void
	───╯
	Finished analysing file 'AoE2ScenarioParser.xs'.


XS-Check errors origins:

  ⇒ [Trigger #0] 'My Trigger With XS'
     ↳ [Effect #0] Script Call Effect


Open the file below to view the entire XS file:
	file:///C:/Users/.../AppData/Local/Temp/tmp_3bgcg8p.xs

-------------------------<[ END XS-CHECK VALIDATION RESULT ]>-------------------------
```


---

# 消息 Messages


# Messages

You can use the message manager to edit the text fields in the `Messages` tab in the in-game editor.

## Editing

Here's an example of how to edit all the fields in the message manager.

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

# File & Folder setup
# Define paths to the scenario folder.
# You can find this folder by opening AoE2:DE and going to scenarios and clicking on 'open folder'
scenario_folder = "your/path/to/the/scenario/folder/"  # <-- Final slash is important
scenario_name = "name_of_your_scenario"

# Define Scenario file
scenario = AoE2DEScenario.from_file(f"{scenario_folder}{scenario_name}.aoe2scenario")

message_manager = scenario.message_manager

message_manager.instructions  = "Do this. Do that... please."
message_manager.hints         = "Don't build 3 Archery Ranges on a neutral island. ¯\_(ツ)_/¯"
message_manager.history       = "* Old man voice * Back in my day we .."
message_manager.loss          = "Better luck next time!"
message_manager.scouts        = "The amount of wood on this map... It's all I can see..."
message_manager.victory       = "VICTORY IS OURS!"

# Write to same folder with name + '_output'
scenario.write_to_file(f"{scenario_folder}{scenario_name}_output.aoe2scenario")
```


---

# 示例 General


# General

### Convert a scenario to/from Return of Rome

> [!WARNING]
> Make sure units on the map are valid for the target variant, and that your scenario is on version **v1.49 or later** (open it in the in-game editor and save once).

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.scenario_variant import ScenarioVariant

scenario = AoE2DEScenario.from_file("your_scenario.aoe2scenario")

scenario.variant = ScenarioVariant.ROR   # Convert to Return of Rome
scenario.variant = ScenarioVariant.AOE2  # Convert back to AoE2

scenario.write_to_file("your_scenario_output.aoe2scenario")
```


---

# 示例 Triggers


# Trigger Examples

### Add a trigger with a condition and effect

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.player_data import Player
from AoE2ScenarioParser.datasets.units import UnitInfo

scenario = AoE2DEScenario.from_file("your_scenario.aoe2scenario")
trigger_manager = scenario.trigger_manager

trigger = trigger_manager.add_trigger("Villager Check")

trigger.new_condition.own_objects(
    source_player=Player.ONE,
    object_list=UnitInfo.VILLAGER.ID,
    quantity=10,
)
trigger.new_effect.send_chat(
    source_player=Player.ONE,
    message="Player 1 has 10 villagers!",
)

scenario.write_to_file("your_scenario_output.aoe2scenario")
```

---

### Enable or disable a trigger

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

scenario = AoE2DEScenario.from_file("your_scenario.aoe2scenario")
trigger_manager = scenario.trigger_manager

for trigger in trigger_manager.triggers:
    if trigger.name == "My Trigger":
        trigger.enabled = False  # Set to True to enable

scenario.write_to_file("your_scenario_output.aoe2scenario")
```

---

### Create a looping trigger

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.player_data import Player

scenario = AoE2DEScenario.from_file("your_scenario.aoe2scenario")
trigger_manager = scenario.trigger_manager

trigger = trigger_manager.add_trigger("Looping Trigger", looping=True)
trigger.new_effect.send_chat(
    source_player=Player.ONE,
    message="This fires every time conditions are met!",
)

scenario.write_to_file("your_scenario_output.aoe2scenario")
```

---

### Copy a trigger for each player

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.player_data import Player

scenario = AoE2DEScenario.from_file("your_scenario.aoe2scenario")
trigger_manager = scenario.trigger_manager

trigger = trigger_manager.add_trigger("Per Player Trigger")
trigger.new_condition.own_objects(
    source_player=Player.ONE,
    quantity=5,
)

# Creates a copy of the trigger for each player, replacing player references
trigger_manager.copy_trigger_per_player(
    from_player=Player.ONE,
    trigger_select=trigger.trigger_id,
    create_copy_for_players=[Player.TWO, Player.THREE, Player.FOUR],
)

scenario.write_to_file("your_scenario_output.aoe2scenario")
```

---

### Replace a sound name across all triggers

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

scenario = AoE2DEScenario.from_file("your_scenario.aoe2scenario")

for trigger in scenario.trigger_manager.triggers:
    for effect in trigger.effects:
        if effect.sound_name == "OldName":
            effect.sound_name = "NewName"

scenario.write_to_file("your_scenario_output.aoe2scenario")
```

---

### Import triggers from another scenario

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

source = AoE2DEScenario.from_file("source.aoe2scenario")
target = AoE2DEScenario.from_file("target.aoe2scenario")

# Import all triggers from source into the beginning of target (index 0)
# Omit the index to append them to the end instead
target.trigger_manager.import_triggers(source.trigger_manager.triggers, 0)

target.write_to_file("target_output.aoe2scenario")
```


---

# 示例 Units


# Unit Examples

### Add a unit to the map

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.units import UnitInfo

scenario = AoE2DEScenario.from_file("your_scenario.aoe2scenario")
unit_manager = scenario.unit_manager

unit_manager.add_unit(player=PlayerId.ONE, unit_const=UnitInfo.ARCHER.ID, x=10, y=10)

scenario.write_to_file("your_scenario_output.aoe2scenario")
```

---

### Remove all units of a specific type

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.units import UnitInfo

scenario = AoE2DEScenario.from_file("your_scenario.aoe2scenario")
unit_manager = scenario.unit_manager

for unit in unit_manager.filter_units_by_const([UnitInfo.ARCHER.ID]):
    unit_manager.remove_unit(unit=unit)

scenario.write_to_file("your_scenario_output.aoe2scenario")
```

---

### Change ownership of units in an area

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

scenario = AoE2DEScenario.from_file("your_scenario.aoe2scenario")
unit_manager = scenario.unit_manager

units = unit_manager.get_units_in_area(x1=0, y1=0, x2=20, y2=20)
unit_manager.change_ownership(units, to_player=PlayerId.TWO)

scenario.write_to_file("your_scenario_output.aoe2scenario")
```

---

### Remove all eye candy (decorative GAIA objects)

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

scenario = AoE2DEScenario.from_file("your_scenario.aoe2scenario")

scenario.unit_manager.remove_eye_candy()

scenario.write_to_file("your_scenario_output.aoe2scenario")
```


---

# 示例 Map


# Map Examples

### Change terrain in an area

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.terrains import TerrainId

scenario = AoE2DEScenario.from_file("your_scenario.aoe2scenario")
map_manager = scenario.map_manager

for tile in map_manager.get_square_1d(x1=0, y1=0, x2=20, y2=20):
    tile.terrain_id = TerrainId.BEACH

scenario.write_to_file("your_scenario_output.aoe2scenario")
```

---

### Set elevation in an area

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

scenario = AoE2DEScenario.from_file("your_scenario.aoe2scenario")
map_manager = scenario.map_manager

# Creates a hill — surrounding terrain adjusts automatically
map_manager.set_elevation(elevation=4, x1=10, y1=10, x2=20, y2=20)

scenario.write_to_file("your_scenario_output.aoe2scenario")
```

---

### Resize the map

> [!WARNING]
> The maximum supported map size is `480x480`. Going above this will cause the game to crash.

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

scenario = AoE2DEScenario.from_file("your_scenario.aoe2scenario")

scenario.map_manager.map_size = 120

scenario.write_to_file("your_scenario_output.aoe2scenario")
```


---

# 示例 Players


# Player Examples

### Set a player's civilization

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.object_support import Civilization

scenario = AoE2DEScenario.from_file("your_scenario.aoe2scenario")
player_manager = scenario.player_manager

player_manager.players[PlayerId.ONE].civilization = Civilization.BRITONS

scenario.write_to_file("your_scenario_output.aoe2scenario")
```

---

### Set starting resources

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

scenario = AoE2DEScenario.from_file("your_scenario.aoe2scenario")
player_manager = scenario.player_manager

player = player_manager.players[PlayerId.ONE]
player.food  = 500
player.wood  = 500
player.gold  = 250
player.stone = 250

scenario.write_to_file("your_scenario_output.aoe2scenario")
```

---

### Set diplomacy between players

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.trigger_lists import DiplomacyState

scenario = AoE2DEScenario.from_file("your_scenario.aoe2scenario")
player_manager = scenario.player_manager

# Set players 1, 3 as one team and players 2, 4 as another — both ways
player_manager.set_diplomacy_teams([PlayerId.ONE, PlayerId.THREE], [PlayerId.TWO, PlayerId.FOUR])

scenario.write_to_file("your_scenario_output.aoe2scenario")
```

---

### Set starting age

```py
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.object_support import StartingAge

scenario = AoE2DEScenario.from_file("your_scenario.aoe2scenario")
player_manager = scenario.player_manager

player_manager.players[PlayerId.ONE].starting_age = StartingAge.CASTLE_AGE

scenario.write_to_file("your_scenario_output.aoe2scenario")
```


---

# 社区与贡献


# Community

## Projects

**AoE2 Tetris** by T-West — A playable Tetris scenario. [Repo](https://github.com/twestura/aoe2tetris) · [Video](https://www.youtube.com/shorts/9ZMobR31qdE) · [Mod](https://www.ageofempires.com/mods/details/21466/)

**Perk Pandemonium** by Alian713 — [Repo](https://github.com/Divy1211/perk_pandemonium_aoe2de) · [Mod](https://www.ageofempires.com/mods/details/19751/)

---

## Tools

**AoE2 DE Scenario Translator** by theunwisewolf — Translate scenarios to any language. [Repo](https://github.com/theunwisewolf/aoe2-scenario-translator)

**AoE2ScenarioStringEditor** *(outdated)* by andistrasser — Edit scenario text content outside the editor. [Repo](https://github.com/andistrasser/AoE2ScenarioStringEditor/tree/dev)

---

## Resources

**Setting up Python, PyCharm and the Parser**

- [Age of Kings Heaven Post](https://aok.heavengames.com/cgi-bin/forums/display.cgi?action=ct&f=4,44777,,30) by **Bassefrom** — written guide with images covering the full installation process.
- [YouTube video](https://www.youtube.com/watch?v=6dP-pDbFCNw&feature=youtu.be) by **duyhung2h** — video walkthrough of the installation process.

**Community Examples**

- [AoE2ScenarioParserTutorial](https://github.com/duyhung2h/AoE2ScenarioParserTutorial) by **duyhung2h** — a GitHub repo with documented examples covering a wide range of parser features, including Python and PyCharm conventions.

---

> [!TIP]
> Built something with AoE2ScenarioParser? Share it in the [Discord server](https://discord.gg/DRUtmugXT3) and it may be added here!