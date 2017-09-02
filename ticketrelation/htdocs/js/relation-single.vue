<template>

        <div>
        <input v-model='relation.value' :name='"field_" + relation.name + "_" + relation.role' type='hidden' />
        <a :href='"/ticket/" + relation.value' v-if='relation.value'> #{{relation.value}} {{relation.ticket? relation.ticket.attributers['summary']: ''}} </a>
        <img :src='"/chrome/ticketrelation/images/search.png"' @click='selectTicket' />
        <img :src='"/chrome/ticketrelation/images/add.png"' @click='addNew' />
        </div>

</template>

<script>
    var PopupCenter = require("./popup.js");
    module.exports = {
        props: ['relation'],
        methods: {
            selectTicket: function () {
                var w = PopupCenter('/select_tickets?type=' + this.relation.targetType, 'select a ticket', '720', '480');
                w.focus();
                var $this = this;
                var timer = setInterval(function() {
                    if (w.closed) {
                        clearInterval(timer);
                        if (w.result) {
                            $this.setValue(w.result);
                        }
                        else {
                            $this.setValue('');
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
                        $this.setValue(w.location.pathname.substring('/ticket/'.length));
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