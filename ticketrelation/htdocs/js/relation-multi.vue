<template>

        <div>
        <input v-model='relation.value' :name='"field_" + relation.name + "_" + relation.role' type='hidden' />
        <p v-for='id in ids' style='margin: 0;'>
            <a :href='"/ticket/" + id'> #{{id}} </a>
            <img src="/chrome/ticketrelation/images/delete.png" @click='remove(id)' />
        </p>
        <img src="/chrome/ticketrelation/images/search.png" @click='selectTicket' />
        <img src="/chrome/ticketrelation/images/add.png" @click='addNew' />
        </div>

</template>

<script>
    var PopupCenter = require("./popup.js");
    module.exports = {
        props: ['relation'],
        computed: {
            ids: function () {
                if (this.relation.value) return this.relation.value.split(',');
                else return [];
            }
        },
        methods: {
            remove: function (id) {
                if (this.relation.value) {
                    var ids = this.relation.value.split(',');
                    var index = ids.indexOf(id);
                    if (index > -1) {
                        ids.splice(index, 1);
                    }
                    this.relation.value = ids.join(',');
                }
            },

            add: function (newids) {
                for (var i in newids.split(',')) {
                    var id = newids.split(',')[i];
                    if (this.relation.value) {
                        var ids = this.relation.value.split(',');
                        var index = ids.indexOf(id);
                        if (index == -1) {
                            ids.push(id);
                        }
                        this.relation.value = ids.join(',');
                    }
                    else {
                        this.relation.value = id;
                    }
                }
            },

            selectTicket: function () {
                var w = PopupCenter('/select_tickets?type=' + this.relation.targetType, 'select a ticket', '720', '480');
                w.focus();
                var $this = this;
                var timer = setInterval(function() {
                    if (w.closed) {
                        clearInterval(timer);
                        if (w.result) {
                            $this.add(w.result);
                        }
                    }
                }, 500);
            },

            addNew: function () {
                var w = PopupCenter('/newticket?type=' + this.relation.targetType, 'new ticket', '720', '480');
                w.focus();
                var $this = this;
                var timer = setInterval(function() {
                    if (w.closed) {
                        clearInterval(timer);
                    }
                    else if (w.location.pathname.startsWith('/ticket/')) {
                        clearInterval(timer);
                        $this.add(w.location.pathname.substring('/ticket/'.length));
                        w.close();
                    }
                }, 500);
            },

            setValue: function (value) {
                this.relation.value = value;
            }
        }
    };
</script>