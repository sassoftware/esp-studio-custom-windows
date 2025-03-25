# Event Sorter Custom Window

This custom window enables you to sort incoming events by a time field that defines when the events were created, as opposed to when they are available to the event stream. Due to message queue throughput or device buffering, events might be presented to the event stream out of chronological order. In order to sort incoming events, an internal buffer of events must be created, which can then be sorted. The size of this buffer is controlled by the configuration, which creates a delay. All incoming records are buffered for the specified length of time. This creates a latency, so you must consider what is the appropriate buffer length for your purposes.  



[toc]

## Installation

Upload the `EventSort.lua` configuration file to SAS Event Stream Processing Studio. For more information, see [Upload a Configuration File](https://documentation.sas.com/?cdcId=espcdc&cdcVersion=default&docsetId=espstudio&docsetTarget=n1s1yakz9sl8upn1h9w2w7ba2mao.htm#p0a64jblkf46y4n1hofcs1ikonrz) in SAS Help Center.

An example ESP project is included in the `files` directory of this repository.  

## Example Usage

In this simple example, data from the International Space Station (ISS) data is read from a file. This data has been intentionally sorted in reverse order to show the effectiveness of the custom window.

![	](Images/{F01CA333-71B2-4420-8D74-D8B9355EA2BB}.png)	

The ISS time field is written in human readable format. The second window, which is a Lua window, is used to convert the human readable time into Linux epoch time. This field is used as the sort field. The last window is the custom window, which performs the sorting.  

The custom window needs to be configured to match your project's schema. In this example, the data consists of a latitude field, a longitude field, and a time field. The fields are mapped as follows: 

![Input Mappings](Images/{CD15F14C-C55E-4D6C-BDC7-64F679305733}.png)	

The field that is used for sorting must be part of your input map. In this example, the relevant field is `epochtime`. The sorting delay is in microseconds, so a value of `1,000,000` represents a 1-second delay. The event stream has a latency that is equal to the `config_sort_delay` field. That is, if you make this delay 10 minutes, all of your records are delayed by 10 minutes. 	

## Example Output

Here is an example of the 44 ISS events that are processed. They are read in starting at key 0 and ending with key 43 at 18:41:47.  

![Example Input](Images/{6018F173-2130-48C6-8644-887C9BADA77C}.png)	

In the **EventSort** tab the events have been sorted and the keys are reversed. However, the date and time column is now correctly showing the older records appearing last.  

![Example Output 2		](Images/{9803D65D-1FEE-4FD5-83F7-B36594CDA998}.png)	
