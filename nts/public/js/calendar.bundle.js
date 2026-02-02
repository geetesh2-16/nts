import { Calendar as FullCalendar } from "@fullcalendar/core";
import dayGridPlugin from "@fullcalendar/daygrid";
import listPlugin from "@fullcalendar/list";
import timeGridPlugin from "@fullcalendar/timegrid";
import interactionPlugin from "@fullcalendar/interaction";

nts.FullCalendar = FullCalendar;
nts.FullCalendar.Plugins = [listPlugin, dayGridPlugin, timeGridPlugin, interactionPlugin];
