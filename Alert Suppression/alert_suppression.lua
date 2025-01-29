local SETTINGS = {}
local USE_SYSTEM_TIME = 0
local lastAlertTimestamps = {} -- table to store the last alert timestamp for each alert group
local alertCounts = {} -- table to store alert counts within COUNT_INTERVAL
local first_event_flag = 1
local stmpFieldName

-- Logging context name
local LOGGING_CONTEXT = "DF.ESP.CUSTOM.CV_ANNOTATION"

-- Initialization function
function init(settings)
    
    
    SETTINGS = settings
    -- preprocessing
    stmpFieldName = SETTINGS["ALERT_TIME_FIELD"]
end

-- Helper function to clean up old alerts beyond COUNT_INTERVAL
local function cleanup_old_alerts(alert_group)
    local current_time = os.time()
    local threshold_time = current_time - tonumber(SETTINGS["COUNT_INTERVAL"])

    if alertCounts[alert_group] then
        local new_alerts = {}
        for _, timestamp in ipairs(alertCounts[alert_group]) do
            if timestamp >= threshold_time then
                table.insert(new_alerts, timestamp)
            end
        end
        alertCounts[alert_group] = new_alerts
    end
end

function create(data, context)
    local event = {}
    local current_stmp

    -- Get the current timestamp from the alert or using system time
    if data[stmpFieldName] then
        if first_event_flag == 1 then
            esp_logMessage(LOGGING_CONTEXT, "Field with name: '" .. tostring(stmpFieldName) .. "' exists in the input event schema, and will be used as timestamp for suppression", "info")
            first_event_flag = 0
        end
        
        current_stmp = tonumber(data[stmpFieldName])
    else
        if first_event_flag == 1 then
            esp_logMessage(LOGGING_CONTEXT, "Field with name: '" .. tostring(stmpFieldName) .. "' doesn't exist in the input event schema, system time will be used instead", "info")
            first_event_flag = 0
        end
        USE_SYSTEM_TIME = 1
        current_stmp = esp_getSystemMicro()
    end

    -- Alerts suppression logic
    local alert_group = data.alert_group or "default"
    if not alertCounts[alert_group] then
        alertCounts[alert_group] = {}
    end

    -- Add the current alert timestamp to the group
    table.insert(alertCounts[alert_group], current_stmp)

    -- Cleanup old alerts outside of COUNT_INTERVAL
    if tonumber(SETTINGS["COUNT_INTERVAL"]) > 0 then
        cleanup_old_alerts(alert_group)
    end

    -- Suppression logic based on MIN_COUNT and COUNT_INTERVAL
    if tonumber(SETTINGS["MIN_COUNT"]) > 0 and #alertCounts[alert_group] < tonumber(SETTINGS["MIN_COUNT"]) then
        event.alert_suppressed = 1
        
        if SETTINGS["LOG_SUPPRESSED_EVENTS"] == "1" then
            esp_logMessage(LOGGING_CONTEXT, "Alert ID="..data.alert_id.." suppressed for group:'" .. alert_group .. "'; Reason: low alert frequency '" .. #alertCounts[alert_group] .. "' where expected is '"..SETTINGS["MIN_COUNT"] .. "' for the COUNT_INTERVAL = " ..SETTINGS["COUNT_INTERVAL"].." seconds", "info")
        end
    
    else
        local last_timestamp = lastAlertTimestamps[alert_group]
        if last_timestamp and ((current_stmp - last_timestamp) / 1e6) < tonumber(SETTINGS["SUPPRESSION_PERIOD"]) then
            -- Suppress the alert
            event.alert_suppressed = 1
        
            if SETTINGS["LOG_SUPPRESSED_EVENTS"] == "1" then
                esp_logMessage(LOGGING_CONTEXT, "Alert ID="..data.alert_id.." suppressed for group:'" .. alert_group .. "'; Reason: already was sent alert at ".. os.date("%Y-%m-%d %H:%M:%S", (last_timestamp/1e6)) .." in the SUPPRESSION_PERIOD = " ..  SETTINGS["SUPPRESSION_PERIOD"].." seconds", "info")
            end
        
        
        
        else
            -- Update the timestamp for this group
            lastAlertTimestamps[alert_group] = current_stmp
            event.alert_suppressed = 0
        end
    end

    -- Output the event
    event.alert_id = data.alert_id
    event.alert_group = alert_group
    event.alert_stmp = current_stmp


    if SETTINGS["OUTPUT_SUPPRESSED_EVENTS"] == "1" or event.alert_suppressed == 0 then
        return event
    end
end


_espconfig_ = {
    settings = {
        desc = "",
        expand_parms = false,
        process_blocks = false,
        encode_binary = false
    },
    inputVariables = {
        desc = "...",
        fields = {
            {
                name = "alert_id",
                desc = "unique alert key, will be a key in the output schema",
                optional = false
            },
            {
                name = "alert_group",
                desc = "if missing default group will be assigned and warning message will be sent to the log",
                optional = true
            },
            {
                name = "alert_stmp",
                desc = "can be set in SETTINGS[ALERT_TIME_FIELD], if field is missing system time will be used instead and info message will be sent to the log",
                optional = true
            },
            {
                name = "alert_group_stmp",
                desc = "only required when SETTINGS[USE_EXTERNAL_CACHE] = 1 ",
                optional = true
            }
        }
    },
    outputVariables = {
        desc = "...",
        fields = {
            {
                name = "alert_id",
                desc = "propagated from input"
            },
            {
                name = "alert_group",
                desc = "propagated from input"
            },
            {
                name = "alert_stmp",
                desc = "propagated from input"
            },
            {
                name = "alert_suppressed",
                desc = "suppression flag"
            }
        }
    },
    initialization = {
        desc = "...",
        fields = {
            {
                name = "ALERT_TIME_FIELD",
                desc = "The name of a time field (string) from the input event schema to use for calculating the suppression period. If not set or the field name does not exist in the event metadata, the system time will be used instead.",
                default = "alert_stmp"
            },
            {
                name = "SUPPRESSION_PERIOD",
                desc = "An integer number of seconds after which all alerts should be suppressed after the first. The period works for unique alert_group. When the period ends, the first new event passes, and the suppressed period is renewed.",
                default = "10"
            },
            {
                name = "USE_EXTERNAL_CACHE",
                desc = "Where to store the suppression period state. If set to 0, the state will be stored only in the Lua window. In this case, we do not support HA and autoscaling in K8ts for the project. If set to 1, the current state will come as the alert_group_stmp field from the input window, and the project will be stateless and autoscalable. The cache can be stored in any persistent storage, we recommend implementing the cache using Redis (see the project template)",
                default = "0"
            },
            {
                name = "OUTPUT_SUPPRESSED_EVENTS",
                desc = "Output suppressed events from the window (with alert_suppressed = 1  ) ",
                default = "1"
            },
            {
                name = "LOG_SUPPRESSED_EVENTS",
                desc = "Output every suppressed events to the pod log",
                default = "1"
            },
            {
                name = "MIN_COUNT",
                desc = "Allowed minimum number of alerts in a given alert_group in the last COUNT_INTERVAL seconds.A value of '0' or no setting means that this mode is disabled.",
                default = "2"
            },
            {
                name = "COUNT_INTERVAL",
                desc = "The number of seconds during which the number of alerts in the alert_group will be counted and compared to the MIN_COUNT. If it is less, the alert will be suppressed. A value of '0' or no setting means that this mode is disabled.",
                default = "10"
            }
        }
    }
}
--[[metadata start
{
    "name": "Alert Suppression",
    "description": "....",
    "tags": [
        "lua",
        "test"
    ],
    "versionNotes": "Added MIN_COUNT and COUNT_INTERVAL logic"
}
metadata end]]--

_espconfig_ = {
    settings = {
        desc = "",
        expand_parms = false,
        process_blocks = false,
        encode_binary = false
    },
    inputVariables = {
        desc = "...",
        fields = {
            {
                name = "alert_id",
                desc = "unique alert key, will be a key in the output schema",
                optional = false
            },
            {
                name = "alert_group",
                desc = "if missing default group will be assigned and warning message will be sent to the log",
                optional = true
            },
            {
                name = "alert_stmp",
                desc = "can be set in SETTINGS[ALERT_TIME_FIELD], if field is missing system time will be used instead and info message will be sent to the log",
                optional = true
            },
            {
                name = "alert_group_stmp",
                desc = "only required when SETTINGS[USE_EXTERNAL_CACHE] = 1 ",
                optional = true
            }
        }
    },
    outputVariables = {
        desc = "...",
        fields = {
            {
                name = "alert_id",
                desc = "propagated from input"
            },
            {
                name = "alert_group",
                desc = "propagated from input"
            },
            {
                name = "alert_stmp",
                desc = "propagated from input"
            },
            {
                name = "alert_suppressed",
                desc = "suppression flag"
            }
        }
    },
    initialization = {
        desc = "...",
        fields = {
            {
                name = "ALERT_TIME_FIELD",
                desc = "The name of a time field (string) from the input event schema to use for calculating the suppression period. If not set or the field name does not exist in the event metadata, the system time will be used instead.",
                default = "alert_stmp"
            },
            {
                name = "SUPPRESSION_PERIOD",
                desc = "An integer number of seconds after which all alerts should be suppressed after the first. The period works for unique alert_group. When the period ends, the first new event passes, and the suppressed period is renewed.",
                default = "10"
            },
            {
                name = "USE_EXTERNAL_CACHE",
                desc = "Where to store the suppression period state. If set to 0, the state will be stored only in the Lua window. In this case, we do not support HA and autoscaling in K8ts for the project. If set to '1', the current state will come as the alert_group_stmp field from the input window, and the project will be stateless and autoscalable. The cache can be stored in any persistent storage, we recommend implementing the cache using Redis (see the project template)",
                default = "0"
            },
            {
                name = "OUTPUT_SUPPRESSED_EVENTS",
                desc = "Output suppressed events from the window (with alert_suppressed = 1  ) ",
                default = "1"
            },
            {
                name = "LOG_SUPPRESSED_EVENTS",
                desc = "Output every suppressed event to the pod log",
                default = "1"
            },
            {
                name = "MIN_COUNT",
                desc = "Allowed minimum number of alerts in a given alert_group in the last COUNT_INTERVAL seconds.A value of '0' or no setting means that this mode is disabled.",
                default = "2"
            },
            {
                name = "COUNT_INTERVAL",
                desc = "The number of seconds during which the number of alerts in the alert_group will be counted and compared to the MIN_COUNT. If it is less, the alert will be suppressed. A value of '0' or no setting means that this mode is disabled.",
                default = "10"
            }
        }
    }
}
--[[metadata start
{
    "name": "Alert Suppression",
    "description": "....",
    "tags": [
        "lua",
        "test"
    ],
    "versionNotes": "Added MIN_COUNT and COUNT_INTERVAL logic"
}
metadata end]]--
