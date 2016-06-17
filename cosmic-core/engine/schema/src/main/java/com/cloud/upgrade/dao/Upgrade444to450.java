// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

package com.cloud.upgrade.dao;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class Upgrade444to450 extends Upgrade442to450 implements DbUpgrade {

    final static Logger s_logger = LoggerFactory.getLogger(Upgrade444to450.class);

    @Override
    public String[] getUpgradableVersionRange() {
        return new String[] {"4.4.4", "4.5.0"};
    }
}