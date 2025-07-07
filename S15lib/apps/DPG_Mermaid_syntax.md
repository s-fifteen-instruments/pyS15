Mermaid-like Syntax for Digital Pattern Generator (DPG_Mermaid_parser.py)

This document outlines the keywords and syntax used in the input file for DPG_Mermaid_parser.py. The file defines blocks of operations, their configurations, and the logical flow between them.
I. General Syntax Elements (Handled by MermaidParser)

    Block Definition:
        Purpose: Defines a named block of operations or configurations.
        Syntax:

        block_id [
            # Content specific to the block type
            keyword1 value1
            keyword2 valueA valueB
            ...
        ]

        or for very simple, single-line content: block_id [ content_keyword value ]
        block_id: A unique alphanumeric name for the block. The prefix of this ID (e.g., "seq", "control") often determines the block type.
        [...]: Encloses the block's content.
        Content: Parsed by the specific Block subclass (e.g., ControlBlock, SeqBlock).

    Loop Block (Subgraph) Definition:
        Purpose: Defines a loop structure that can contain other blocks and logic.
        Syntax:

        subgraph loop_id [
            # Optional: Loop Name Comment (e.g., # My Detailed Loop)
            # Loop Initialization Line (ivar, count, optional chan/dac)
        ]
            # Internal logic connections for the loop body
            block_in_loop_A --> block_in_loop_B
            block_in_loop_B --> loop_check 
            ...

        end

        subgraph: Keyword indicating the start of a loop block definition.
        loop_id: A unique alphanumeric name for the loop block. Block IDs starting with "loop" are treated as LoopBlocks.
        [...]: Encloses the loop's definition (initialization line). Any other logic internal logic goes between here and the end
        end: Terminates the loop

    Logic Connections:
        Purpose: Defines the execution flow between blocks.
        Syntax:
            source_block_id --> target_block_id
            source_block_id --> |condition_label| target_block_id
        -->: Arrow indicating a directed connection.
        |condition_label|: Optional label for conditional branches (e.g., |success|, |failure|, |high|, |low|). Used by TriggerBlock and BranchBlock.

    Comments:
        Full-Line Mermaid Comments: Lines starting with %%. These are ignored by the main parser. %% This whole line is a comment
        Block-Internal/End-of-Line Comments: Text following a # symbol on a line within a block's content or on a logic connection line. keyword value # This part is a comment blockA --> blockB # Comment about this connection
        Name Comments: The first line inside a block's [...] definition, if it starts with #, is often used as a descriptive name for that block by the specific block parsers (e.g., for SeqBlock, TriggerBlock, LoopBlock, BranchBlock).

    flowchart Keyword:
        Lines starting with flowchart (e.g., flowchart TD) are ignored by the main parser.

II. Keywords by Block Type

(Block types are typically determined by the prefix of the block_id)
A. control Block

(Identified by block_id starting with "control". Content within controlXYZ [...])

    clock <freq_value_unit> [<selection_mode>]
        Defines system clock.
        <freq_value_unit>: E.g., 100mhz, 50khz.
        <selection_mode>: Optional. auto (default), external, internal, direct.
        Example: clock 100mhz auto
    evars <val1> [<val2> <val3> <val4>]
        Sets initial values for up to 4 external variables (0-65535).
        Example: evars 1000 0 500
    ivars <val1> [<val2> <val3> <val4>]
        Sets initial values for up to 4 internal variables (0-65535).
        Example: ivars 10 20
    auxout <polarity>
        Sets auxiliary output line polarity.
        <polarity>: 0, 1, nim, or ttl.
        Example: auxout nim
    dacconfig <mode>
        Sets DAC configuration mode.
        <mode>: static, single, half, full.
        Example: dacconfig full
    version <type>
        Sets pattern generator hardware version.
        <type>: 64bit or 128bit.
        Example: version 128bit
    inlevel <polarity>
        Sets external input level threshold polarity.
        <polarity>: 0, 1, nim, or ttl.
        Example: inlevel ttl
    auxconfig <mode>
        Sets auxiliary output line configuration mode.
        <mode>: normal, delayed, main, ref.
        Example: auxconfig delayed
    startaddress <addr>
        Sets pattern execution start address.
        <addr>: Integer < 512.
        Example: startaddress 0
    dacstatic <ch:val> [<ch:val> ...]
        Sets static values for DACs of 128bit DPG.
        <ch:val>: E.g., 0:1.0V, 1:2000. Values can be integers or voltage floating strings.
        Example: dacstatic 0:0 1:32768

B. seq Block

(Identified by block_id starting with "seq". Content within seqXYZ [...]) Each line (after an optional name comment) defines a step with the following structure: [<time>] [use_ivar <idx>] [chan <channels>] [dac <dac_updates>] [#<comment>]

    <time> (Mandatory): Duration, e.g., 10ns, 20us.
    use_ivar <idx> (Optional): Multiplies step duration by ivar <idx> (0-3).
        Example: 10ns use_ivar 0 ...
    chan [<channel_list>] (Keyword chan is mandatory, list can be empty): Defines active digital channels.
        <channel_list>: Numbers or ranges, e.g., 0 2-4 7. If empty after chan, all channels for this step will be off (depends on previous state or hardware default).
        Example: ... chan 0 1 5-7 ...
    dac <dac_updates> (Optional): Updates the set DAC value for selected channel/s. Only 1 DAC value allowed per step
        <dac_updates>: ch:val pairs, e.g., 0:15000, 1:100, 0:2.5V, 3: -1.1V
        Example: ... dac 0:-1.0V 2:-1.0V ...

C. trigger Block

(Identified by block_id starting with "trigger". Content within triggerXYZ [...])

    extinput <eN>: Specifies external input e1 to e4.
        Example: extinput e1
    chan [<channel_list>]: Digital channels active during trigger logic execution.
        Example: chan 0 5
    dac <dac_updates>: DAC values during trigger logic execution.
        Example: dac 0:3000
    rate <freq_value_unit>: Trigger based on event rate. Cannot be used with count.
        Example: rate 50khz
    count <N> in <time_span_value_unit>: Trigger on <N> events in <time_span>. Cannot be used with rate. <N>, <eN>  must match the evars value set in control
        Example: count 10 in 1ms
    success <block_id>: Block to jump to on trigger success.
        Example: success nextBlock
    failure <block_id>: Block to jump to on trigger failure.
        Example: failure errorRoutine

D. loop Block

(Identified by block_id starting with subgraph loop_id [...]  end syntax. Content within subgraph loop_id [...] end) The first content line (after optional name comment) is the initialization line: ivar <idx> <value> [chan <channels>] [dac <dac_updates>]

    ivar <idx> <value> (Mandatory on init line): Defines loop counter ivar <idx> (0-3) and iteration count <value> (1-65535).
        Example: ivar 0 100 ...
    chan [<channel_list>] (Optional on init line): Channels active during loop control operations.
        Example: ... chan 1 2 ...
    dac <dac_updates> (Optional on init line): DACs values during loop control operations.
        Example: ... dac 1:500 ...
    Internal Logic: Subsequent lines outside the [...] are logic connections forming the loop body.
        loop_check: Special target ID. source_block --> loop_check means end current iteration and check counter.

E. branch Block

(Identified by block_id starting with "branch". Content within branchXYZ [...])

    extinput <eN>: Specifies external input e1 to e4 for decision.
        Example: extinput e2
    high <block_id>: Block to jump to if extinput is high.
        Example: high pathA
    low <block_id>: Block to jump to if extinput is low.
        Example: low pathB
    chan [<channel_list>] (Optional): Channels active during branch input check.
        Example: chan 3
    dac <dac_updates> (Optional): DACs values during branch input check.
        Example: dac 2:1.2V
    <time> (Optional, on its own line): Duration for the branch check hardware instruction(s). E.g., 50ns. If not specified, a default minimum timestep is used by the translator.
