

function PopupCenter(url, title, w, h) {
    // Fixes dual-screen position                         Most browsers      Firefox
    var dualScreenLeft = window.screenLeft != undefined ? window.screenLeft : screen.left;
    var dualScreenTop = window.screenTop != undefined ? window.screenTop : screen.top;

    var width = window.innerWidth ? window.innerWidth : document.documentElement.clientWidth ? document.documentElement.clientWidth : screen.width;
    var height = window.innerHeight ? window.innerHeight : document.documentElement.clientHeight ? document.documentElement.clientHeight : screen.height;

    var left = ((width / 2) - (w / 2)) + dualScreenLeft;
    var top = ((height / 2) - (h / 2)) + dualScreenTop;
    var newWindow = window.open(url, title, 'scrollbars=yes, width=' + w + ', height=' + h + ', top=' + top + ', left=' + left);

    // Puts focus on the newWindow
    if (window.focus) {
        newWindow.focus();
    }

    return newWindow;
}

Vue.component('relation-single', {
    template: "\
        <div> \
        <input v-model='relation.value' :name='\"field_\" + relation.name + \"_\" + relation.role' type='hidden' /> \
        <a :href='\"/ticket/\" + relation.value' v-if='relation.value'> #{{relation.value}} {{relation.ticket? relation.ticket.attributers['summary']: ''}} </a> \
        <img :src='\"/chrome/ticketrelation/images/search.png\"' @click='selectTicket' /> \
        <img :src='\"/chrome/ticketrelation/images/add.png\"' @click='addNew' /> \
        </div> \
    ",
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
})


Vue.component('relation-multi', {
    template: "\
        <div> \
        <input v-model='relation.value' :name='\"field_\" + relation.name + \"_\" + relation.role' type='hidden' /> \
        <p v-for='id in ids' style='margin: 0;'> \
            <a :href='\"/ticket/\" + id'> #{{id}} </a> \
            <img :src='\"/chrome/ticketrelation/images/delete.png\"' @click='remove(id)' /> \
        </p> \
        <img :src='\"/chrome/ticketrelation/images/search.png\"' @click='selectTicket' /> \
        <img :src='\"/chrome/ticketrelation/images/add.png\"' @click='addNew' /> \
        </div> \
    ",
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
})