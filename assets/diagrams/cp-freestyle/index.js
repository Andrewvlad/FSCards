// Moves have no native key, so they are keyed in the order they appear in the doc
const _CpFreestyle = {
    names: {
        // Group 1
        1: "Crane",
        2: "Can-Can",
        3: "Cross-up",
        4: "Nac-Nac",
        5: "T",
        6: "Flex Head",
        7: "Method",
        // Group 2
        8: "Superman",
        9: "Walnut",
        10: "Boomerang",
        11: "Lazy Boy",
        // Group 3
        12: "Switchblade",
        13: "Switchcow",
        // Group 4
        14: "Lazyswitch",
        15: "Blind Man",
        16: "Boomcow",
        17: "Blindboom",
        18: "Cowboy",
        19: "Ghost Rider",
        20: "Tick Jockey",
        // Group 5
        21: "Lazyghost",
        22: "Miracle Man",
        23: "Wingover",
    },
    classes: [
        // Technically called moves, rather than blocks
        {key: '1', label: 'Group 1', blocks: [1, 2, 3, 4, 5, 6, 7]},
        {key: '2', label: 'Group 2', blocks: [8, 9, 10, 11]},
        {key: '3', label: 'Group 3', blocks: [12, 13]},
        {key: '4', label: 'Group 4', blocks: [14, 15, 16, 17, 18, 19, 20]},
        {key: '5', label: 'Group 5', blocks: [21, 22, 23]},
        {key: 'all', label: 'All'},
    ],
    sets: { USPA: null },
    includeCaption: true,
    fusions: [14, 16],
};
