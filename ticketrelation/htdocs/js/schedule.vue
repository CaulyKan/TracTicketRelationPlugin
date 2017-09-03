<template>
    <div>
        <div v-for="ticketInfo, relationName in schedule" >
            <schedule-item :relationName="relationName" :tickets="ticketInfo"></schedule-item>
        </div>
    </div>
</template>
<script>
    module.exports = {
        props: ['schedule'],
        methods: {
        }
    }
</script>