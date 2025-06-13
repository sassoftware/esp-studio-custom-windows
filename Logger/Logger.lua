local SETTINGS = {}
local writtenHeaders = {}

-- Logging context name
local LOGGING_CONTEXT = "DF.ESP.CUSTOM.LOGGER"

-- Initialization function
function init(settings)   
    SETTINGS = settings
end


local writtenHeaders = {}

function microToReadable(micro)
    local seconds = math.floor(micro / 1e6) -- Convert microseconds to whole seconds
    local milliseconds = math.floor((micro % 1e6) / 1e3) -- Extract milliseconds
    local formatted = os.date("%Y-%m-%d %H:%M:%S", seconds) .. string.format(".%03d", milliseconds)
    return formatted
end

function split(str, delimiter)
    local result = {}
    for match in string.gmatch(str, "[^" .. delimiter .. "]+") do
        table.insert(result, match)
    end
    return result
end

function inlist(tbl, item)
    for _, value in ipairs(tbl) do
        if value == item then
            return true
        end
    end
    return false
end


function convertEventData_tbl(event_tbl, delimiter)
    delimiter = delimiter or "|"

    if type(event_tbl) ~= "table" then
        return "Error: Input is not a table"
    end

    local headers = {}
    local values = {}

    for key, value in pairs(event_tbl) do
        table.insert(headers, tostring(key))
        table.insert(values, tostring(value))
    end

    if #headers == 0 then
        return "Error: No headers found"
    end

    if #values == 0 then
        return "Error: No values found"
    end

    local headers_str = table.concat(headers, delimiter)
    local values_str = table.concat(values, delimiter)

    return headers_str, values_str
end


function generateLogFilename(context)
    local filename = context or "default" -- Use 'default' if no context name provided
    return SETTINGS["LOG_DIR"] .. filename .. "_log.csv"
end

function logEventToFile(event, context)
    local filename = generateLogFilename(context)
    local file = io.open(filename, "a")
    if file then
        local log_entry = event
        file:write(log_entry .. "\n")
        file:close()
    else
        esp_logMessage(LOGGING_CONTEXT, "Error: Unable to open file for logging", "error")
    end
end

local i = 0

function create(data, context)
    local event = {}
    if i < tonumber(SETTINGS["LOG_MAX_EVENTS"]) then
        if inlist(split(SETTINGS["LOG_WINDOWS_LIST"], ","), context.input) then
            local timestamp_micro = tonumber(esp_getSystemMicro())
            event.log_id = i
            event.window = context.input
            event.received_timestamp = timestamp_micro
            event.received_timestamp_str = microToReadable(timestamp_micro)

            --esp_logMessage(LOGGING_CONTEXT, "event data:" .. tostring(data) .. "event window:" .. context.input, "info")

            -- Get headers and data from event
            local headers, log_data = convertEventData_tbl(data, ",")
            event.event_data = log_data

            -- Increment event count
            i = i + 1

            -- Get headers and data from event

            -- Handle logging to separate files or default log file
            if tonumber(SETTINGS["LOG_TO_SEPARATE_FILES"]) == 1 then
                if not writtenHeaders[context.input] then
                    logEventToFile("LOGGER_received_timestamp,LOGGER_id,LOGGER_received_timestamp_str,LOGGER_window,"..headers, context.input)
                    writtenHeaders[context.input] = true
                end
                logEventToFile(event.received_timestamp..","..event.log_id..","..event.received_timestamp_str ..","..event.window.."," .. log_data, context.input)
            else
                logEventToFile("LOGGER_received_timestamp,LOGGER_id,LOGGER_received_timestamp_str,LOGGER_window,"..headers)
                logEventToFile(event.received_timestamp..","..event.log_id..","..event.received_timestamp_str ..","..event.window.."," .. log_data)
            end

            return event
        end
    end
end


_espconfig_ = {
    settings = {
        desc = "",
        expand_parms = false,
        process_blocks = false,
        encode_binary = true
    },
    outputVariables = {
        desc = "Output event details",
        fields = {
            {
                name = "log_id",
                desc = "Internal log row sequence number",
                esp_type = "int64"
            },
            {
                name = "window",
                desc = "SAS ESP Input Window Name",
                esp_type = "string"
            },
            {
                name = "received_timestamp",
                desc = "System timestamp of file entry creation",
                esp_type = "stamp"
            },
            {
                name = "received_timestamp_str",
                desc = "The system timestamp in human-readable string format ('%Y-%m-%d %H:%M:%S') when the file entry was created",
                esp_type = "string"
            },
            {
                name = "event_data",
                desc = "All input event field data, separated by commas",
                esp_type = "string"
            }
        }
    },
    initialization = {
        desc = "Initialization settings",
        fields = {
            {
                name = "LOG_MAX_EVENTS",
                desc = "Number of events to write to log file(s). 0 means the logger is disabled.",
                default = "100"
            },
            {
                name = "LOG_WINDOWS_LIST",
                desc = "List of window names where to log events, separated by commas. All windows must be connected to the logger window by an edge in the SAS ESP model graph."
            },
            {
                name = "LOG_DIR",
                desc = "The destination where the log files will be written. If the SAS ESP does not have permissions to create/modify a file in this folder, an error message will be added to the SAS ESP's main log.",
                default = "@ESP_PROJECT_OUTPUT@/"
            },
            {
                name = "LOG_TO_SEPARATE_FILES",
                desc = "If set to 1, a separate CSV file will be created for each input window.",
                default = "1"
            }
        }
    }
}
--[[metadata start
{
    "name": "Logger",
    "description": "This window automatically saves to file all events from ESP Windows that you can select using the LOG_WINDOWS_LIST environment variable. Logging can be easily disabled/enabled when the SAS ESP container starts using the LOG_MAX_EVENTS variable.",
    "tags": [
        "logger",
        "lua"
    ],
    "versionNotes": "next version"
}
metadata end]]--
