def render_bb8_status(
    ts,
    model,
    identifier,
    rssi,
    uuid,
    paired=None,
    bonded=None,
    tx_power=None,
    path=None,
):
    # Use N/A for missing values
    paired_str = f"{paired}" if paired is not None else "N/A"
    bonded_str = f"{bonded}" if bonded is not None else "N/A"
    tx_power_str = f"{tx_power}" if tx_power is not None else "N/A"
    uuid_str = uuid or "N/A"
    path_str = path or "N/A"
    return f""".  * '   .    * .    '     .    '     * .    '     * .       .  '   .
     .           .    * .      '     .    * .'     .    * .'     .
╔═════════════════════════════════════════════════════════════════════╗
║///////////////// [ H O M E S T A T I O N // STATUS ] ///////////////║
╚═════════════════════════════════════════════════════════════════════╝
 '     .    .     * .      * .    '    .     * .    '     * .    '
     .    * '    .  .     * '     .  .     * '      .   . * .    ' * .
 ┌─[ SYSTEM CORE ]────────────────────────────────────────────────┐
 │ >_ TIMESTAMP:      {ts}               .   │
 │ >_ SCANNER:        [ OPERATIONAL ]                           * │
 │ >_ BEACON:         [ ACQUIRED ]                            '   │
 │ >_ STATUS:         [ BB-8 ONLINE ]                             │
 │ >_ CONNECTION:     [ OFFLINE ]                .        .       │
 └────────────────────────────────────────────────────────────────┘
 .    * '  .     .       * .    .     '      * '    .   .  '
     .  * '    .  .  '      * .    '    .   * .    . '              '
 ┌─[ PERIPHERAL: BB-8 ]──────────────────┐  * '    .      . * '    .
 │ >_ MODEL:          {model}        │ '   .   * .    '
 │ >_ IDENTIFIER:     {identifier}  │     .    '    .
 │ >_ SIGNAL (RSSI):  {rssi} dBm            │  .    '    .     .
 └───────────────────────────────────────┘     * '     .    * '    .
 '     .   .     * .   * .  .     .       '   .     .     *
 .    .    * '    .  .     * '     .  .     * '      .  * '    .
 ┌─[ ADAPTER_HCI0 ]──────────────────────────────────────────────────┐
 │ >_ PATH:           {path_str}          │
 │ >_ UUID:           {uuid_str}           │
 │ >_ SECURITY:       [ PAIRED: {paired_str} ] [ BONDED: {bonded_str} ]        . │
 │ >_ TX_POWER:       {tx_power_str}                                              │
 └───────────────────────────────────────────────────────────────────┘
 '   .    * '    .      * .    '    .     * .         * '    .    .
    .    * .  .     .        .  '      * .  '  .   *      * '    .   .
══════════════════════════════════════════════════════════════════════
 >_ LOG: Displaying current device state. Awaiting next scan cycle...
══════════════════════════════════════════════════════════════════════"""
