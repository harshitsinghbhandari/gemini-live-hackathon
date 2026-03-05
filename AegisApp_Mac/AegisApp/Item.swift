//
//  Item.swift
//  AegisApp
//
//  Created by Harshit Singh Bhandari on 05/03/26.
//

import Foundation
import SwiftData

@Model
final class Item {
    var timestamp: Date
    
    init(timestamp: Date) {
        self.timestamp = timestamp
    }
}
