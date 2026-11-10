/**
 * @file libcomp/src/Message.cpp
 * @ingroup libcomp
 *
 * @author COMP Omega <compomega@tutanota.com>
 *
 * @brief Base message class.
 *
 * This file is part of the COMP_hack Library (libcomp).
 *
 * Copyright (C) 2012-2021 COMP_hack Team <compomega@tutanota.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "Message.h"

#include "BaseScriptEngine.h"

using namespace libcomp;

namespace libcomp {
template <>
BaseScriptEngine &BaseScriptEngine::Using<Message::Message>() {
  if (!BindingExists("Message.Message")) {
    Sqrat::Class<Message::Message, Sqrat::NoConstructor<Message::Message>>
        binding(mVM, "Message.Message");
    Bind("Message.Message", binding);

    binding.Func("GetType", &Message::Message::GetRawType)
        .Func("GetRawType", &Message::Message::GetRawType)
        .Func("Dump", &Message::Message::Dump)
        .Prop("Type", &Message::Message::GetRawType)
        .Prop("RawType", &Message::Message::GetRawType);
  }

  return *this;
}
}  // namespace libcomp
