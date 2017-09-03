<template>
    <div>
        <div class="schedule_header">
            <h3>{{displayName}}</h3>
        </div>
        <div>
            <table>
                <tr>
                    <td width="20%"> </td>
                    <td>
                        <table>
                            <tbody>
                                <tr>
                                    <td class="schedule_today schedule_date_right" v-if="todayStatus=='right-most'" >Today ▼</td>
                                    <td class="schedule_today schedule_date_right" v-else-if="todayStatus=='beyond-right'">Today ({{diffDate(finishDate, now)}}) ▶</td>
                                    <td class="schedule_today" v-else-if="todayStatus=='beyond-left'">◀ Today ({{diffDate(now, startDate)}})</td>
                                    <td class="schedule_today" v-else :width="todayPosition"></td>
                                    <td class="schedule_today schedule_today_fix" v-show="todayStatus=='normal'">▼ Today</td>
                                </tr>
                            </tbody>
                        </table>
                    </td>
                </tr>
            </table>
            <div v-for="ticket in tickets">
                <table>
                    <tbody>
                        <tr>
                            <td width="20%">
                                <div class="schedule_ticket_header">
                                    <a :href="ticket.id">#{{ticket.id}} {{ticket.summary}} </a>
                                </div>
                                <div class="schedule_ticket_header_status">{{ticket.status}}</div>
                            </td>
                            <td>
                                <table class="schedule_table" v-if="isPlanAvailable(ticket)">
                                    <tbody>
                                        <tr class="schedule_date_row">
                                            <td class="schedule_leading_space" :width="getPlanSpaces(ticket)[0]"></td>
                                            <td class="schedule_date_cell" :width="getPlanSpaces(ticket)[1]">
                                                <div class="schedule_date_left">{{getDateStr(ticket.activity_start_date)}}</div>
                                                <div class="schedule_date_right">{{getDateStr(ticket.activity_finish_date)}}</div>
                                            </td>
                                            <td class="schedule_following_space" :width="getPlanSpaces(ticket)[2]"></td>
                                        </tr>
                                        <tr class="schedule_plan_row">
                                            <td class="schedule_leading_space" :width="getPlanSpaces(ticket)[0]"></td>
                                            <td class="schedule_bar" :width="getPlanSpaces(ticket)[1]"></td>
                                            <td class="schedule_following_space" :width="getPlanSpaces(ticket)[2]"></td>
                                        </tr>
                                    </tbody>
                                </table>
                                <table class="schedule_table" v-if="isActualAvailable(ticket)">
                                    <tbody>
                                        <tr class="schedule_actual_row">
                                            <td class="schedule_leading_space" :width="getActualSpaces(ticket)[0]"></td>
                                            <td class="schedule_bar" :width="getActualSpaces(ticket)[1]"></td>
                                            <td class="schedule_following_space" :width="getActualSpaces(ticket)[2]"></td>
                                        </tr>
                                        <tr class="schedule_date_row">
                                            <td class="schedule_leading_space" :width="getActualSpaces(ticket)[0]"></td>
                                            <td class="schedule_date_cell" :width="getActualSpaces(ticket)[1]">
                                                <div class="schedule_date_left">{{getDateStr(ticket.activity_started_date)}}</div>
                                                <div class="schedule_date_right">{{getDateStr(ticket.activity_finished_date == null? now: ticket.activity_finished_date)}}</div>
                                            </td>
                                            <td class="schedule_following_space" :width="getActualSpaces(ticket)[2]"></td>
                                        </tr>
                                    </tbody>
                                </table>
                                <div v-if="!isPlanAvailable(ticket) && !isActualAvailable(ticket)">No available schedule info.</div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <table>
                <tr>
                    <td width="20%"> </td>
                    <td>
                        <table>
                            <tbody>
                            <tr>
                                <td class="schedule_today schedule_date_right" v-if="todayStatus=='right-most'" >Today ▲</td>
                                <td class="schedule_today schedule_date_right" v-else-if="todayStatus=='beyond-right'">Today ({{diffDate(finishDate, now)}}) ▶</td>
                                <td class="schedule_today" v-else-if="todayStatus=='beyond-left'">◀ Today ({{diffDate(now, startDate)}})</td>
                                <td class="schedule_today" v-else :width="todayPosition"></td>
                                <td class="schedule_today schedule_today_fix" v-show="todayStatus=='normal'">▲ Today</td>
                            </tr>
                            </tbody>
                        </table>
                    </td>
                </tr>
            </table>
        </div>
    </div>
</template>
<script>
    module.exports = {
        props: ['relationName', 'tickets'],
        created: function() {
            var self = this;
            this.tickets.forEach(function(t) {
                t.activity_start_date = self.toDate(t.activity_start_date);
                t.activity_started_date = self.toDate(t.activity_started_date);
                t.activity_finish_date = self.toDate(t.activity_finish_date);
                t.activity_finished_date = self.toDate(t.activity_finished_date);
            });
        },
        computed: {
            name: function () {
                return this.relationName.split(',')[0];
            },
            displayName: function () {
                return this.relationName.split(',')[1];
            },
            startDate: function () {
                var result = null;
                this.tickets.forEach(function (t) {
                    if (t.activity_start_date instanceof Date && (t.activity_start_date < result || result == null)) {
                        result = t.activity_start_date;
                    }
                    if (t.activity_started_date instanceof Date && (t.activity_started_date < result || result == null)) {
                        result = t.activity_started_date;
                    }
                });
                return result;
            },
            finishDate: function () {
                var result = null;
                this.tickets.forEach(function (t) {
                    if (t.activity_finish_date instanceof Date && (t.activity_finish_date > result || result == null)) {
                        result = t.activity_finish_date;
                    }
                    if (t.activity_finished_date instanceof Date && (t.activity_finished_date > result || result == null)) {
                        result = t.activity_finished_date;
                    }
                    if (t.activity_finished_date == null && t.activity_started_date instanceof Date) {
                        if (this.now > result || result == null) {
                            result = this.now;
                        }
                    }
                });
                return result;
            },
            totalDays: function () {
                return this.diffDate(this.startDate, this.finishDate);
            },
            todayStatus: function () {
                if (this.getDateStr(this.finishDate) == this.getDateStr(this.now)) {
                    return 'right-most';
                }
                else if (this.now > this.finishDate) {
                    return 'beyond-right';
                }
                else if (this.now < this.startDate) {
                    return 'beyond-left';
                }
                else return 'normal';
            },
            todayPosition: function () {
                return (this.diffDate(this.startDate, this.now) / this.totalDays * 100) + '%';
            },
            now: function () {
                return this.toDate(new Date(Date.now()));
            }
        },
        methods: {
            isPlanAvailable: function (ticket) {
                return ticket.activity_finish_date instanceof Date && ticket.activity_start_date  instanceof Date;
            },
            isActualAvailable: function (ticket) {
                if (!ticket.activity_started_date instanceof Date) return false;
                if (ticket.activity_finished_date instanceof Date) return true;
                if (ticket.activity_finished_date == null) return true;
                return false;
            },
            getPlanSpaces: function(ticket) {
                if (this.isPlanAvailable(ticket)) {
                    return [
                        (this.diffDate(this.startDate, ticket.activity_start_date) / this.totalDays * 100) + '%',
                        (this.diffDate(ticket.activity_start_date, ticket.activity_finish_date) / this.totalDays * 100) + '%',
                        (this.diffDate(ticket.activity_finish_date, this.finishDate) / this.totalDays * 100) + '%',
                    ];
                }
                else return [0,0,0];
            },
            getActualSpaces: function(ticket) {
                if (this.isActualAvailable(ticket)) {
                    var fn = ticket.activity_finished_date == null? this.now: ticket.activity_finished_date;
                    return [
                        (this.diffDate(this.startDate, ticket.activity_started_date) / this.totalDays * 100) + '%',
                        (this.diffDate(ticket.activity_started_date, fn) / this.totalDays * 100) + '%',
                        (this.diffDate(fn, this.finishDate) / this.totalDays * 100) + '%',
                    ];
                }
                else return [0,0,0];
            },
            diffDate: function (date1, date2) {
                return parseInt((date2 - date1)/(24*3600*1000));
            },
            isDate: function (data) {
                if (data instanceof Date && data.toString() != "Invalid Date") return True;
                if (typeof(data) == 'string' ) {
                    var result = new Date(data);
                    return result.toString() != "Invalid Date";
                }
                else return false;
            },
            toDate: function (data) {
                if (typeof(data) == 'string' && this.isDate(data)) {
                    var date = new Date(data);
                    var y = date.getFullYear();
                    var m = date.getMonth();
                    var d = date.getDate();
                    return new Date(y, m, d, 0, 0, 0);
                }
                else if (data instanceof Date) {
                    var date = data;
                    var y = date.getFullYear();
                    var m = date.getMonth();
                    var d = date.getDate();
                    return new Date(y, m, d, 0, 0, 0);
                }
                else return data;
            },
            getDateStr: function (date) {
                var y = date.getFullYear();
                var m = date.getMonth() + 1;
                var d = date.getDate();
                return y + '-' + m + '-' + d;
            }
        }
    }
</script>