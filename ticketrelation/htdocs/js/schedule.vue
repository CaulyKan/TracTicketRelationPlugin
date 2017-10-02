<template>
    <div>
        <div v-for="ticketInfo, relationName in schedule" >
            <schedule-item :relationName="relationName" :tickets="ticketInfo" :config="config"></schedule-item>
        </div>
    </div>
</template>
<script>
    module.exports = {
        props: ['schedule', 'config'],
    }
</script>