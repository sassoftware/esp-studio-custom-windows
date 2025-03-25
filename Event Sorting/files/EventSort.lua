local EventSortInject = {}
EventSortInject.__index = EventSortInject

------------------------------------
---  Class functions 
------------------------------------

-- Constructor (return new object)
function EventSortInject:init(options)
    local self = setmetatable({}, EventSortInject)
    self.myclass = "EventSortInject"
    self.options = options or {}  -- Store options if provided
    self.SortEventsTable = {}  -- create new table
    self.bufferStack = {}   -- stack incoming events to implement locking. 
    self.SortNeeded = True 
    self.SortField=nil  -- This field is passed to us from the settings. 
    self.SortDelay=nil 
    self.SortEventsTableLock=false
    self.debugg = false 
    
    print("************************* " .. self.myclass .. " initialized **********************************")
    return self
end

-- Second function (example method)
function EventSortInject:printMessage(message)
    if self.debugg then 
        print(self.myclass .. " says:" )
        print(esp_toString(message))
    end     
end

-- -- Function to flush buffer to main table when it's not locked
function EventSortInject:flushBuffer(context)
     if not self.SortEventsTableLock then
        while #self.bufferStack > 0 do
            local item = table.remove(self.bufferStack)
            self:addEventEntry(item,context) 
        end
    end
    
end


-- Function to add incoming data to the buffer stack
function EventSortInject:addDataToBuffer(data,context)
    table.insert(self.bufferStack, data)
end 

--------------------------------------------------------------------------------
--  Write messages to log
--
--
-- Usage example:
--      self:Logger("This is bad, real bad.","warn",context)
--

function EventSortInject:Logger(
    message,  -- string:  message to convey 
    errorlevel,  -- string:  Possible values of level are as follows:  optional
--                            trace
--                            error
--                            warn
--                            fatal
--                            info
--                            debug
    context)  -- string:  window context  optional

local function validate_input(inputvalue, possiblevalues )
  local answer = false 
  for i, v in ipairs(possiblevalues) do
    if v == inputvalue then
      answer = true 
      break 
    end
  end
  return answer 
end

    local level 
    if errorlevel then 
        local isValid = validate_input(errorlevel,{"trace","error","warn","fatal","info","debug"})
        if isValid then level = errorlevel 
        else level = "info"
        end 
    else  level = "info"
    end     
    
    
    
    local logcontext 
    if context then 
        logcontext = context.window
    else logcontext = self.myclass
    end 
    esp_logMessage(logcontext,message,level,debug.getinfo(1).currentline)

return 
end 
--------------------------------------------------------------------------------
--  Add an event to the table
--
-- 
-- Usage example:
--      ESI:addEventEntry(data,context)
--
function EventSortInject:addEventEntry( 
        data,   -- table:  table for current event
        context) -- string:  window.context reference. optional 
-- return:  nothing.  table entry built inside object.
    data.timeReceived = esp_getSystemMicro() 
    table.insert(self.SortEventsTable,data)
    self.SortNeeded = true  --  if we add something we need a sort.
    
    
return 
end 

--------------------------------------------------------------------------------
--  Sort  the table by sort field. 
--
-- 
-- Usage example:
--      AT:sortEventtable(context)
--

function EventSortInject:sortEventtable( 
        context) -- string:  window.context reference. optional 
-- return:  nothing.  table entry built inside object.
    if self.SortNeeded then 
        if #self.SortEventsTable  > 1 then   -- only sort if more than one entry 
        -- sort backwards so the oldest stuff is on the end. 
        table.sort(self.SortEventsTable, function(a, b) return a[self.SortField] > b[self.SortField] end)
        self.SortNeeded = false 
        end 
    end 
return 
end 

--------------------------------------------------------------------------------
--  Inject expired events into stream and delete from table
--
-- 
-- Usage example:
--      AT:injectEventtable(context)
--

function EventSortInject:injectEventtable( 
        context) -- string:  window.context reference. optional 
-- return:  table of events to be sent into the stream.

local TotalEvents =  #self.SortEventsTable
local Events = {}  -- table of events to return                      
 if TotalEvents  > 0  then   -- we have data 
        local current_time = esp_getSystemMicro()

    for i = TotalEvents, 1, -1 do  -- loop back to front and delete expired records.  
        
       --self:printMessage(self.SortEventsTable)
       self:printMessage(tostring(current_time) .. " " .. tostring(self.SortEventsTable[i]["timeReceived"]) .. " " ..  self.SortDelay )
       if  (current_time - self.SortEventsTable[i]["timeReceived"])  > tonumber(self.SortDelay) then
           self.SortEventsTable[i]["timeReceived"] = nil 
        -- I think adding them from back to front of the queue puts them in reverse order from how I want them.
        --  So I sorted them backward to begin with to fix this issue.         
        table.insert(Events,self.SortEventsTable[i])   -- add to return table 
        table.remove(self.SortEventsTable,i)  -- remove from cache of events 
       end    
    end 
 end   
 
  if #Events > 0 then return Events 
  else return nil 
  end 
end  -- function 

-- Example usage:
local ESI = EventSortInject:init()  -- Create an instance
ESI:printMessage("Hello, world!")   -- Call the print function

function init(fields)
  if fields then  -- do we even have any 
    -- Iterate through the fields table
        ESI:printMessage("Hello, from init method!")   -- Call the print function
        ESI:printMessage(fields) 
        
    for k, v in pairs(fields) do    
        if k == "config_sort_field" then 
            ESI.SortField = v
        end 
        if k == "config_sort_delay" then 
            ESI.SortDelay = v
        end 
    end
    ESI:printMessage("saved fields: " .. ESI.SortField .. tostring(ESI.SortDelay) )   -- Call the print function
    --print("saved fields: ",ESI.SortField , ESI.SortDelay )   -- Call the print function
    
  end
end 

function create(data,context)
    
    
    ESI:addDataToBuffer(data,context)  -- buffer incoming records when main table is locked. 
    
    ESI:flushBuffer(context)  -- flush buffer when unlocked. 
    
    return(events)
end

function heartbeat(context)
    local events = nil 
    
     ESI.SortEventsTableLock=true  -- lock the table for writes
     ESI:printMessage("Hello, from heartbeat method!")   -- Calnl the print function
     ESI:sortEventtable(context)   -- sort table according to specified sort field. 
     events = ESI:injectEventtable(context)  -- stream sorted events after the time has passed. 
     ESI.SortEventsTableLock=false   -- unlock 
    
    return(events)
end

_espconfig_ = {
    settings = {
        desc = "",
        expand_parms = false,
        process_blocks = false,
        encode_binary = false
    },
    inputVariables = {
        desc = "",
        fields = {
            {
                name = "epochtime",
                desc = "linux epoch time in microseconds.",
                optional = false
            },
            {
                name = "dt",
                desc = "readable data and time ",
                optional = false
            },
            {
                name = "lat",
                desc = "latitude ",
                optional = false
            },
            {
                name = "long",
                desc = "longitude ",
                optional = false
            },
            {
                name = "key",
                desc = "event key field ",
                optional = false
            }
        }
    },
    outputVariables = {
        desc = "",
        fields = {
            {
                name = "Out1",
                desc = "Manditory but unused "
            }
        }
    },
    initialization = {
        desc = "",
        fields = {
            {
                name = "config_sort_field",
                desc = "Name of schema entry which contains sort variable",
                default = "epochtime"
            },
            {
                name = "config_sort_delay",
                desc = "number of microseconds to queue events for sorting ",
                default = "1000000"
            }
        }
    }
}
--[[metadata start
{
    "name": "EventSort",
    "description": "Sort incoming events so that they are injected into the stream in time order.  ",
    "tags": []
}
metadata end]]--